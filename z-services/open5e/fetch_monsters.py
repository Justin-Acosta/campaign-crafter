import requests
import os
import sys

# Base URL for Open5e API (for stats)
OPEN5E_URL = "https://api.open5e.com/v1/monsters/"

# Base URL for D&D 5e API (for images)
DND5EAPI_URL = "https://www.dnd5eapi.co"

def get_mod(score):
    """Calculates the ability modifier."""
    mod = (score - 10) // 2
    return f"{'+' if mod >= 0 else ''}{mod}"

def fetch_monster_image(name):
    """
    Fetches monster image from D&D 5e API.
    """
    # Convert name to slug format used by dnd5eapi (e.g., "Ogre Zombie" -> "ogre-zombie")
    slug = name.lower().replace(" ", "-")
    url = f"{DND5EAPI_URL}/api/monsters/{slug}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            image_path = data.get("image")
            if image_path:
                return f"{DND5EAPI_URL}{image_path}"
    except requests.RequestException:
        pass
    
    return None

def download_image(image_url, monster_slug, output_dir="creatures/images"):
    """
    Downloads an image and saves it locally.
    """
    if not image_url:
        return None
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            # Get extension from URL or default to png
            ext = image_url.split(".")[-1]
            filename = f"{monster_slug}.{ext}"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return filepath
    except requests.RequestException:
        print(f"Failed to download image for {monster_slug}")
        
    return None

def fetch_monster(name):
    """
    Fetches monster data from Open5e API by name.
    """
    # Search for the monster
    params = {"search": name}
    try:
        response = requests.get(OPEN5E_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['count'] == 0:
            print(f"No monster found for '{name}'")
            return None
        
        # Filter for exact match first
        results = data['results']
        exact_match = next((m for m in results if m['name'].lower() == name.lower()), None)
        
        if exact_match:
            return exact_match
            
        # Fallback to first result if no exact match
        return results[0]
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def format_monster_md(monster, local_image_path=None):
    """
    Formats monster data into a Markdown stat block.
    """
    md = f"# {monster['name']}\n"
    
    if local_image_path:
        # Use workspace-absolute path starting with / so it works from any directory
        # Assuming local_image_path is like "creatures/images/skeleton.png"
        # We want "/creatures/images/skeleton.png"
        # We can just prepend / to the relative path from workspace root
        
        # Ensure we have a path relative to workspace root
        # The download_image function returns path relative to workspace root (e.g. creatures/images/file.png)
        
        # Just verify it doesn't already start with /
        workspace_path = local_image_path if local_image_path.startswith("/") else f"/{local_image_path}"
        
        md += f"![{monster['name']}]({workspace_path})\n\n"
        
    md += f"**Challenge** {monster.get('challenge_rating', 'Unknown')} ({monster.get('xp', '0')} XP)\n\n"
    md += f"*{monster['size']} {monster['type']}, {monster['alignment']}*\n"
    
    md += f"**Armor Class** {monster['armor_class']} ({monster.get('armor_desc', '') or 'natural armor'})\n"
    md += f"**Hit Points** {monster['hit_points']} ({monster['hit_dice']})\n"
    md += f"**Speed** {monster.get('speed', {}).get('walk', 0)} ft.\n\n"
    
    # Calculate stats and modifiers
    stats = {
        "STR": f"{monster['strength']} ({get_mod(monster['strength'])})",
        "DEX": f"{monster['dexterity']} ({get_mod(monster['dexterity'])})",
        "CON": f"{monster['constitution']} ({get_mod(monster['constitution'])})",
        "INT": f"{monster['intelligence']} ({get_mod(monster['intelligence'])})",
        "WIS": f"{monster['wisdom']} ({get_mod(monster['wisdom'])})",
        "CHA": f"{monster['charisma']} ({get_mod(monster['charisma'])})"
    }

    # formatting helper for table alignment
    def pad(text, width):
        return f"{text}".center(width, " ")

    md += f"|{pad('STR', 11)}|{pad('DEX', 11)}|{pad('CON', 11)}|{pad('INT', 11)}|{pad('WIS', 11)}|{pad('CHA', 11)}|\n"
    md += "|:---------:|:---------:|:---------:|:---------:|:---------:|:---------:|\n"
    md += f"|{pad(stats['STR'], 11)}|{pad(stats['DEX'], 11)}|{pad(stats['CON'], 11)}|{pad(stats['INT'], 11)}|{pad(stats['WIS'], 11)}|{pad(stats['CHA'], 11)}|\n\n"
    
    # Skills, Senses, Languages, Challenge
    if monster.get('skills'):
        skills_str = ", ".join([f"{k} +{v}" for k, v in monster['skills'].items()])
        md += f"**Skills** {skills_str}\n"
    
    md += f"**Senses** {monster.get('senses', '')}\n"
    md += f"**Languages** {monster.get('languages', '')}\n\n"
    
    # Special Abilities
    if monster.get('special_abilities'):
        md += "## Traits\n"
        for ability in monster['special_abilities']:
            md += f"***{ability['name']}.*** {ability['desc']}\n\n"
            
    # Actions
    if monster.get('actions'):
        md += "## Actions\n"
        for action in monster['actions']:
            md += f"***{action['name']}.*** {action['desc']}\n\n"
            
    # Legendary Actions
    if monster.get('legendary_actions'):
        md += "## Legendary Actions\n"
        md += "The monster can take 3 legendary actions, choosing from the options below. Only one legendary action option can be used at a time and only at the end of another creature's turn. The monster regains spent legendary actions at the start of its turn.\n\n"
        for action in monster['legendary_actions']:
            md += f"***{action['name']}.*** {action['desc']}\n\n"

    return md

def save_monster_to_file(monster_name, output_dir="creatures", image_dir="creatures/images"):
    """
    Fetches a monster, downloads its image, and saves it as a markdown file.
    """
    print(f"Fetching {monster_name}...")
    monster_data = fetch_monster(monster_name)
    
    if monster_data:
        # Try to fetch and download image
        image_url = fetch_monster_image(monster_name)
        local_image_path = None
        if image_url:
            print(f"  Found image for {monster_name}, downloading...")
            local_image_path = download_image(image_url, monster_data['slug'], image_dir)
        
        md_content = format_monster_md(monster_data, local_image_path)
        
        # Create directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        filename = f"{monster_data['slug']}.md"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(md_content)
        
        print(f"Saved {monster_data['name']} to {filepath}")
        return filepath
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_monsters.py <monster_name1> [monster_name2 ...]")
        print("Example: python fetch_monsters.py 'skeleton' 'zombie' 'ancient green dragon'")
    else:
        for name in sys.argv[1:]:
            save_monster_to_file(name)
