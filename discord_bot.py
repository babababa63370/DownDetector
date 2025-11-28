import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import requests
from config import DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Supabase REST API headers
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def query_supabase(table, query=""):
    """Simple REST API call to Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}{query}"
        resp = requests.get(url, headers=SUPABASE_HEADERS, timeout=5)
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        print(f"Erreur query: {e}")
        return None

async def autocomplete_service_name(interaction: discord.Interaction, current: str) -> list:
    """Autocomplete pour les noms de services"""
    services = query_supabase("services", f"?owner_id=eq.{interaction.user.id}&select=name")
    if not services:
        return []
    
    names = [s["name"] for s in services]
    return [
        discord.app_commands.Choice(name=name, value=name)
        for name in names
        if current.lower() in name.lower()
    ][:25]

@bot.event
async def on_ready():
    print(f"✅ Bot Discord connecté: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} commandes synchronisées")
    except Exception as e:
        print(f"❌ Erreur sync: {e}")
    
    if not check_services.is_running():
        check_services.start()

@bot.tree.command(name="add_service", description="Ajoute un service à monitorer")
async def add_service(interaction: discord.Interaction, url: str, name: str):
    """Ajoute un service"""
    try:
        data = {
            "url": url,
            "name": name,
            "status": "online",
            "owner_id": str(interaction.user.id),
            "guild_id": interaction.guild_id or 0
        }
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/services",
            json=data,
            headers=SUPABASE_HEADERS,
            timeout=5
        )
        if resp.status_code == 201:
            await interaction.response.send_message(f"✅ Service '{name}' ajouté!")
        else:
            await interaction.response.send_message(f"❌ Erreur: {resp.text}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {str(e)}")

@bot.tree.command(name="list_services", description="Liste tes services")
async def list_services(interaction: discord.Interaction):
    """Liste les services"""
    try:
        services = query_supabase("services", f"?owner_id=eq.{interaction.user.id}&select=*")
        
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
    try:
        resp = requests.delete(
            f"{SUPABASE_URL}/rest/v1/services?owner_id=eq.{interaction.user.id}&name=eq.{name}",
            headers=SUPABASE_HEADERS,
            timeout=5
        )
        if resp.status_code in [200, 204]:
            await interaction.response.send_message(f"✅ Service '{name}' supprimé")
        else:
            await interaction.response.send_message(f"❌ Erreur")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {str(e)}")

@remove_service.autocomplete("name")
async def remove_autocomplete(interaction: discord.Interaction, current: str) -> list:
    return await autocomplete_service_name(interaction, current)

@bot.tree.command(name="graph", description="Affiche les stats d'un service")
async def show_graph(interaction: discord.Interaction, name: str):
    """Affiche les stats d'un service"""
    try:
        # Récupère le service
        services = query_supabase("services", f"?owner_id=eq.{interaction.user.id}&name=eq.{name}")
        if not services:
            await interaction.response.send_message(f"❌ Service '{name}' non trouvé")
            return
        
        service = services[0]
        service_id = service['id']
        
        # Récupère les logs
        logs = query_supabase("ping_logs", f"?service_id=eq.{service_id}&order=created_at.desc&limit=100")
        
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
        uptime = int((len([s for s in statuses if s == 'online']) / len(statuses)) * 100) if statuses else 0
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
            color=color
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
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"Erreur graph: {e}")
        await interaction.response.send_message(f"❌ Erreur: {str(e)}")

@show_graph.autocomplete("name")
async def graph_autocomplete(interaction: discord.Interaction, current: str) -> list:
    return await autocomplete_service_name(interaction, current)

@bot.tree.command(name="config_ping", description="Configure l'intervalle de ping (owner only)")
async def config_ping(interaction: discord.Interaction, interval: int):
    """Configure l'intervalle de ping en secondes (owner only)"""
    app_info = await bot.application_info()
    if interaction.user.id != app_info.owner.id:
        await interaction.response.send_message("❌ Seul le propriétaire du bot peut utiliser cette commande!", ephemeral=True)
        return
    
    if interval < 10 or interval > 3600:
        await interaction.response.send_message("❌ L'intervalle doit être entre 10 secondes et 1 heure (3600s)")
        return
    
    check_services.change_interval(minutes=interval/60)
    await interaction.response.send_message(f"✅ Intervalle de ping configuré à **{interval} secondes**")

@tasks.loop(minutes=5)
async def check_services():
    """Vérifie le statut des services"""
    try:
        services = query_supabase("services", "?select=*")
        if not services:
            return
        
        for service in services:
            try:
                import time
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(service["url"], timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        latency_ms = int((time.time() - start_time) * 1000)
                        new_status = "online" if resp.status == 200 else "down"
                        
                        # Enregistre le log
                        requests.post(
                            f"{SUPABASE_URL}/rest/v1/ping_logs",
                            json={
                                "service_id": service["id"],
                                "owner_id": service["owner_id"],
                                "service_name": service["name"],
                                "status": new_status,
                                "latency_ms": latency_ms
                            },
                            headers=SUPABASE_HEADERS,
                            timeout=5
                        )
                        
                        # Update service status
                        requests.patch(
                            f"{SUPABASE_URL}/rest/v1/services?id=eq.{service['id']}",
                            json={"status": new_status},
                            headers=SUPABASE_HEADERS,
                            timeout=5
                        )
            except Exception as e:
                print(f"Erreur check {service.get('name')}: {e}")
    except Exception as e:
        print(f"Erreur check_services: {e}")

@check_services.before_loop
async def before_check():
    await bot.wait_until_ready()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
