import discord
from discord.ext import commands, tasks
import aiohttp
from config import DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

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
    """Ajoute un service à monitorer"""
    if not supabase:
        await interaction.response.send_message("❌ Erreur: Supabase non configuré")
        return
    
    try:
        supabase.table("services").insert({
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
        response = supabase.table("services").select("*").eq("guild_id", interaction.guild_id).execute()
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
        supabase.table("services").delete().eq("guild_id", interaction.guild_id).eq("name", name).execute()
        await interaction.response.send_message(f"✅ Service '{name}' supprimé")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {str(e)}")

@tasks.loop(minutes=5)
async def check_services():
    """Vérifie le statut des services toutes les 5 minutes"""
    if not supabase:
        return
    
    try:
        response = supabase.table("services").select("*").execute()
        all_services = response.data
        
        for service in all_services:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(service["url"], timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        old_status = service.get("status")
                        new_status = "online" if resp.status == 200 else "down"
                        
                        supabase.table("services").update({"status": new_status}).eq("id", service["id"]).execute()
                        
                        if old_status != new_status:
                            guild = bot.get_guild(service["guild_id"])
                            if guild:
                                for channel in guild.text_channels:
                                    try:
                                        emoji = "🟢" if new_status == "online" else "🔴"
                                        await channel.send(
                                            f"{emoji} **{service['name']}** est maintenant **{new_status.upper()}**"
                                        )
                                        break
                                    except Exception:
                                        continue
            except Exception as e:
                print(f"Erreur check {service.get('name')}: {e}")
    except Exception as e:
        print(f"Erreur check_services: {e}")

@check_services.before_loop
async def before_check():
    await bot.wait_until_ready()
