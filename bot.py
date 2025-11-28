import discord
from discord.ext import commands, tasks
import aiohttp
from config import DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY
import asyncio
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Stockage en mémoire (remplacé par Supabase)
monitored_services = {}

@bot.event
async def on_ready():
    print(f"✅ Bot connecté: {bot.user}")
    check_services.start()

@bot.tree.command(name="add_service", description="Ajoute un service à monitorer")
async def add_service(interaction: discord.Interaction, url: str, name: str):
    """Ajoute un service à monitorer"""
    guild_id = interaction.guild_id
    if guild_id not in monitored_services:
        monitored_services[guild_id] = []
    
    monitored_services[guild_id].append({"url": url, "name": name, "status": "online"})
    
    await interaction.response.send_message(f"✅ Service '{name}' ajouté: {url}")

@bot.tree.command(name="list_services", description="Liste les services monitorés")
async def list_services(interaction: discord.Interaction):
    """Liste les services"""
    guild_id = interaction.guild_id
    if guild_id not in monitored_services or not monitored_services[guild_id]:
        await interaction.response.send_message("❌ Aucun service configuré")
        return
    
    services = monitored_services[guild_id]
    embed = discord.Embed(title="🔍 Services Monitorés", color=discord.Color.blue())
    for i, service in enumerate(services, 1):
        status_emoji = "🟢" if service["status"] == "online" else "🔴"
        embed.add_field(
            name=f"{i}. {service['name']}",
            value=f"{status_emoji} {service['url']}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remove_service", description="Supprime un service")
async def remove_service(interaction: discord.Interaction, name: str):
    """Supprime un service"""
    guild_id = interaction.guild_id
    if guild_id in monitored_services:
        monitored_services[guild_id] = [s for s in monitored_services[guild_id] if s["name"] != name]
        await interaction.response.send_message(f"✅ Service '{name}' supprimé")
    else:
        await interaction.response.send_message("❌ Service non trouvé")

@tasks.loop(minutes=5)
async def check_services():
    """Vérifie le statut des services toutes les 5 minutes"""
    for guild_id, services in monitored_services.items():
        for service in services:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(service["url"], timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        old_status = service["status"]
                        new_status = "online" if resp.status == 200 else "down"
                        service["status"] = new_status
                        
                        # Notifier si changement de statut
                        if old_status != new_status:
                            guild = bot.get_guild(guild_id)
                            if guild:
                                for channel in guild.text_channels:
                                    try:
                                        emoji = "🟢" if new_status == "online" else "🔴"
                                        await channel.send(
                                            f"{emoji} **{service['name']}** est maintenant **{new_status.upper()}**"
                                        )
                                        break
                                    except:
                                        continue
            except Exception as e:
                service["status"] = "down"
                print(f"Erreur lors du check de {service['name']}: {e}")

@check_services.before_loop
async def before_check():
    await bot.wait_until_ready()

# Synchroniser les commandes
@bot.event
async def on_ready():
    print(f"✅ Bot prêt: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} commandes synchronisées")
    except Exception as e:
        print(f"❌ Erreur sync: {e}")
    
    check_services.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
