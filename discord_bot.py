import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from config import DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Lazy initialization de Supabase pour éviter les erreurs d'import
_supabase = None

def get_supabase():
    global _supabase
    if _supabase is None:
        if SUPABASE_URL and SUPABASE_KEY:
            from supabase import create_client
            _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

# Configuration du ping interval (en minutes)
ping_interval = 5

@bot.event
async def on_ready():
    print(f"✅ Bot Discord connecté: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} commandes synchronisées")
    except Exception as e:
        print(f"❌ Erreur sync: {e}")
    
    # Crée la table ping_logs si elle n'existe pas
    if get_supabase():
        try:
            get_supabase().table("ping_logs").select("id").limit(1).execute()
        except Exception as e:
            if "Could not find the table" in str(e):
                print("📊 Création de la table ping_logs...")
                try:
                    import os
                    import requests
                    # Crée la table via API Supabase
                    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
                    headers = {
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json"
                    }
                    sql = """
                    CREATE TABLE IF NOT EXISTS ping_logs (
                        id SERIAL PRIMARY KEY,
                        service_id INT NOT NULL,
                        owner_id TEXT NOT NULL,
                        service_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        latency_ms INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_ping_logs_owner ON ping_logs(owner_id);
                    CREATE INDEX IF NOT EXISTS idx_ping_logs_service ON ping_logs(service_id);
                    CREATE INDEX IF NOT EXISTS idx_ping_logs_created ON ping_logs(created_at);
                    """
                    requests.post(url, json={"query": sql}, headers=headers)
                    print("✅ Table ping_logs créée!")
                except Exception as e2:
                    print(f"⚠️ Erreur création table: {e2}")
    
    if not check_services.is_running():
        check_services.start()

@bot.tree.command(name="add_service", description="Ajoute un service à monitorer")
async def add_service(interaction: discord.Interaction, url: str, name: str):
    """Ajoute un service à monitorer"""
    if not supabase:
        await interaction.response.send_message("❌ Erreur: Supabase non configuré")
        return
    
    try:
        get_supabase().table("services").insert({
            "guild_id": interaction.guild_id,
            "name": name,
            "url": url,
            "status": "online",
            "owner_id": str(interaction.user.id)
        }).execute()
        await interaction.response.send_message(f"✅ Service '{name}' ajouté: {url}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {str(e)}")

@bot.tree.command(name="list_services", description="Liste les services monitorés")
async def list_services(interaction: discord.Interaction):
    """Liste les services"""
    if not supabase:
        await interaction.response.send_message("❌ Erreur: Supabase non configuré")
        return
    
    try:
        response = get_supabase().table("services").select("*").eq("owner_id", str(interaction.user.id)).execute()
        services = response.data
        
        if not services:
            await interaction.response.send_message("❌ Aucun service configuré")
            return
        
        embed = discord.Embed(title="🔍 Services Monitorés", color=discord.Color.blue())
        for i, service in enumerate(services, 1):
            status_emoji = "🟢" if service.get("status") == "online" else "🔴"
            embed.add_field(
                name=f"{i}. {service['name']}",
                value=f"{status_emoji} {service['url']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {str(e)}")

@bot.tree.command(name="remove_service", description="Supprime un service")
async def remove_service(interaction: discord.Interaction, name: str):
    """Supprime un service"""
    if not supabase:
        await interaction.response.send_message("❌ Erreur: Supabase non configuré")
        return
    
    try:
        get_supabase().table("services").delete().eq("owner_id", str(interaction.user.id)).eq("name", name).execute()
        await interaction.response.send_message(f"✅ Service '{name}' supprimé")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {str(e)}")

@bot.tree.command(name="graph", description="Affiche les stats et graphique d'un service")
async def show_graph(interaction: discord.Interaction, name: str):
    """Affiche les stats d'un service avec lien vers graphique interactif"""
    if not supabase:
        await interaction.response.send_message("❌ Erreur: Supabase non configuré")
        return
    
    try:
        # Récupère le service
        services_resp = get_supabase().table("services").select("*").eq("owner_id", str(interaction.user.id)).eq("name", name).execute()
        if not services_resp.data:
            await interaction.response.send_message(f"❌ Service '{name}' non trouvé")
            return
        
        service = services_resp.data[0]
        service_id = service['id']
        
        # Récupère les logs
        logs_resp = get_supabase().table("ping_logs").select("*").eq("service_id", service_id).order("created_at", desc=False).limit(100).execute()
        logs = logs_resp.data
        
        if not logs:
            await interaction.response.send_message(f"❌ Aucun historique pour '{name}'")
            return
        
        # Calcule les stats
        latencies = [l.get('latency_ms', 0) for l in logs]
        valid_latencies = [l for l in latencies if l > 0]
        avg_latency = int(sum(valid_latencies) / len(valid_latencies)) if valid_latencies else 0
        max_latency = max(valid_latencies) if valid_latencies else 0
        min_latency = min(valid_latencies) if valid_latencies else 0
        
        statuses = [l.get('status') for l in logs]
        uptime = int((len([s for s in statuses if s == 'online']) / len(statuses)) * 100)
        down_count = len([s for s in statuses if s == 'offline'])
        
        # Détermine la couleur
        if uptime >= 95:
            color = discord.Color.green()
            status_emoji = "🟢"
        elif uptime >= 80:
            color = discord.Color.yellow()
            status_emoji = "🟡"
        else:
            color = discord.Color.red()
            status_emoji = "🔴"
        
        # Crée l'embed
        embed = discord.Embed(
            title=f"📊 {name}",
            description=f"{status_emoji} **Status:** {service.get('status', 'unknown')}",
            color=color,
            url=f"https://0f19beb3-5918-4629-9b4b-283c0f6e2372-00-2w544i7ovzoww.janeway.replit.dev/dashboard"
        )
        
        embed.add_field(
            name="⏱️ Latence",
            value=f"Moy: **{avg_latency}ms**\nMax: **{max_latency}ms**\nMin: **{min_latency}ms**",
            inline=True
        )
        
        embed.add_field(
            name="✅ Disponibilité",
            value=f"Uptime: **{uptime}%**\nIndisponibilités: **{down_count}**",
            inline=True
        )
        
        embed.add_field(
            name="🔗 Données",
            value=f"Enregistrements: **{len(logs)}**",
            inline=False
        )
        
        embed.set_footer(text="Clic sur le titre pour voir le graphique interactif!")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"Erreur graph: {e}")
        await interaction.response.send_message(f"❌ Erreur: {str(e)}")

@bot.tree.command(name="config_ping", description="Configure l'intervalle de ping (owner only)")
async def config_ping(interaction: discord.Interaction, interval: int):
    """Configure l'intervalle de ping en secondes (owner only)"""
    global ping_interval
    
    # Vérifie si l'utilisateur est le propriétaire du bot
    app_info = await bot.application_info()
    if interaction.user.id != app_info.owner.id:
        await interaction.response.send_message("❌ Seul le propriétaire du bot peut utiliser cette commande!", ephemeral=True)
        return
    
    # Vérifie que l'intervalle est raisonnable (min 10 secondes, max 1 heure)
    if interval < 10 or interval > 3600:
        await interaction.response.send_message("❌ L'intervalle doit être entre 10 secondes et 1 heure (3600s)")
        return
    
    # Convertir en minutes pour la tâche
    new_interval_minutes = interval / 60
    
    # Redémarrer la tâche avec le nouvel intervalle
    check_services.change_interval(minutes=new_interval_minutes)
    ping_interval = interval
    
    await interaction.response.send_message(f"✅ Intervalle de ping configuré à **{interval} secondes** ({new_interval_minutes:.1f} minutes)")
    print(f"🔄 Intervalle de ping changé à {interval}s par {interaction.user.name}")

@tasks.loop(minutes=5)  # Default 5 minutes, can be changed with /config_ping
async def check_services():
    """Vérifie le statut des services toutes les 5 minutes"""
    if not supabase:
        return
    
    try:
        response = get_supabase().table("services").select("*").execute()
        all_services = response.data
        
        for service in all_services:
            try:
                import time
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(service["url"], timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        latency_ms = int((time.time() - start_time) * 1000)
                        old_status = service.get("status")
                        new_status = "online" if resp.status == 200 else "down"
                        
                        get_supabase().table("services").update({"status": new_status}).eq("id", service["id"]).execute()
                        
                        # Enregistre le log de ping
                        get_supabase().table("ping_logs").insert({
                            "service_id": service["id"],
                            "owner_id": service["owner_id"],
                            "service_name": service["name"],
                            "status": new_status,
                            "latency_ms": latency_ms
                        }).execute()
                        
                        if old_status != new_status:
                            guild = bot.get_guild(service["guild_id"])
                            if guild:
                                for channel in guild.text_channels:
                                    try:
                                        emoji = "🟢" if new_status == "online" else "🔴"
                                        await channel.send(
                                            f"{emoji} **{service['name']}** est maintenant **{new_status.upper()}** (latence: {latency_ms}ms)"
                                        )
                                        break
                                    except Exception:
                                        continue
            except asyncio.TimeoutError:
                # Si timeout, enregistre comme down
                get_supabase().table("ping_logs").insert({
                    "service_id": service["id"],
                    "owner_id": service["owner_id"],
                    "service_name": service["name"],
                    "status": "down",
                    "latency_ms": 5000
                }).execute()
                get_supabase().table("services").update({"status": "down"}).eq("id", service["id"]).execute()
            except Exception as e:
                print(f"Erreur check {service.get('name')}: {e}")
    except Exception as e:
        print(f"Erreur check_services: {e}")

@check_services.before_loop
async def before_check():
    await bot.wait_until_ready()
