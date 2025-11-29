import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import requests
from config import DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime, timedelta

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
        print(f"Add service response: {resp.status_code} - {resp.text}")
        if resp.status_code in [200, 201]:
            await interaction.response.send_message(f"✅ Service '{name}' ajouté!")
        else:
            await interaction.response.send_message(f"❌ Erreur: {resp.status_code} - {resp.text}")
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


@bot.tree.command(name="ping_now", description="Force un ping immédiat pour tous les services")
async def ping_now(interaction: discord.Interaction):
    """Force un ping immédiat"""
    await interaction.response.defer()
    try:
        await check_services()
        await interaction.followup.send("✅ Ping lancé! Les données devraient être disponibles maintenant.")
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur: {str(e)}")

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

def create_graph_image(service_name, logs):
    """Crée une image du graphique avec Pillow"""
    if not logs:
        logs = []
    
    # Paramètres du graphique
    width, height = 800, 400
    padding = 50
    graph_width = width - 2 * padding
    graph_height = height - 2 * padding
    
    # Créer l'image
    img = Image.new('RGB', (width, height), color=(36, 37, 38))
    draw = ImageDraw.Draw(img)
    
    # Titre
    title = f"Graphique de latence: {service_name}"
    draw.text((padding, 10), title, fill=(88, 101, 242))
    
    # Axes
    draw.rectangle([padding, padding, padding + graph_width, padding + graph_height], outline=(150, 150, 150))
    
    # Pas de logs
    if not logs or len(logs) < 2:
        draw.text((padding + 100, padding + 150), "Pas assez de données", fill=(200, 200, 200))
        return img
    
    # Extraire les latences
    latencies = [log.get("latency_ms", 0) or 0 for log in logs]
    if max(latencies) == 0:
        draw.text((padding + 100, padding + 150), "Pas de données de latence", fill=(200, 200, 200))
        return img
    
    max_latency = max(latencies) * 1.2  # Ajouter 20% de marge
    
    # Tracer la ligne
    points = []
    for i, latency in enumerate(latencies):
        x = padding + (i / (len(latencies) - 1)) * graph_width if len(latencies) > 1 else padding + graph_width / 2
        y = padding + graph_height - (latency / max_latency) * graph_height
        points.append((x, y))
    
    # Dessiner les points et lignes
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=(87, 242, 135), width=2)
    
    for point in points:
        draw.ellipse([point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3], fill=(87, 242, 135))
    
    # Labels
    draw.text((padding - 30, padding - 20), "Latence (ms)", fill=(200, 200, 200))
    draw.text((padding + graph_width - 50, padding + graph_height + 10), "Temps", fill=(200, 200, 200))
    
    # Stats
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency_actual = max(latencies)
    
    stats_text = f"Moyenne: {avg_latency:.0f}ms | Min: {min_latency}ms | Max: {max_latency_actual}ms"
    draw.text((padding, height - 25), stats_text, fill=(200, 200, 200))
    
    return img

@bot.tree.command(name="graph", description="Affiche le graphique de latence d'un service")
async def graph(interaction: discord.Interaction, name: str = None):
    """Affiche le graphique de latence"""
    await interaction.response.defer()
    try:
        # Récupérer les services de l'utilisateur
        services = query_supabase("services", f"?owner_id=eq.{interaction.user.id}")
        
        if not services:
            await interaction.followup.send("❌ Tu n'as pas de services")
            return
        
        # Si pas de nom spécifié, prendre le premier
        service = None
        if name:
            service = next((s for s in services if s["name"].lower() == name.lower()), None)
        else:
            service = services[0]
        
        if not service:
            await interaction.followup.send(f"❌ Service '{name}' non trouvé")
            return
        
        # Récupérer les logs
        logs = query_supabase("pings", f"?service_id=eq.{service['id']}&order=created_at.asc&limit=100")
        
        if not logs:
            await interaction.followup.send(f"❌ Pas de données pour '{service['name']}'")
            return
        
        # Créer l'image
        img = create_graph_image(service['name'], logs)
        
        # Envoyer l'image
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        file = discord.File(img_bytes, filename="graph.png")
        await interaction.followup.send(file=file)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur: {str(e)}")

@graph.autocomplete("name")
async def graph_autocomplete(interaction: discord.Interaction, current: str) -> list:
    return await autocomplete_service_name(interaction, current)

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
                        
                        # Enregistre le log via REST API (table pings)
                        try:
                            log_resp = requests.post(
                                f"{SUPABASE_URL}/rest/v1/pings",
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
                            if log_resp.status_code in [200, 201]:
                                print(f"✅ Log enregistré: {service['name']} ({latency_ms}ms)")
                            else:
                                print(f"⚠️ Log error: {log_resp.status_code}")
                        except Exception as e:
                            print(f"⚠️ Erreur log: {e}")
                        
                        # Update service status
                        try:
                            requests.patch(
                                f"{SUPABASE_URL}/rest/v1/services?id=eq.{service['id']}",
                                json={"status": new_status},
                                headers=SUPABASE_HEADERS,
                                timeout=5
                            )
                        except Exception as e:
                            print(f"⚠️ Erreur update: {e}")
            except Exception as e:
                print(f"Erreur check {service.get('name')}: {e}")
    except Exception as e:
        print(f"Erreur check_services: {e}")

@check_services.before_loop
async def before_check():
    await bot.wait_until_ready()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
