from setuptools import setup, find_packages

setup(
    name="downdetector",
    version="1.0.0",
    description="Discord bot service monitoring with web dashboard",
    author="Your Name",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "discord.py==2.3.2",
        "flask==3.0.0",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "aiohttp==3.9.1",
        "pillow==10.1.0",
        "supabase==2.8.1",
        "gunicorn==21.2.0",
    ],
)
