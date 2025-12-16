#!/usr/bin/env python3
"""
🚀 SPACE BATTLE - CLIENT
Jeu de combat spatial multijoueur
Contrôles: ZQSD + Souris + Espace pour tirer
"""

import pygame
import socket
import threading
import json
import math
import sys
import time
import base64
import random

# Essaie d'importer PyAudio pour le voice chat
try:
    import pyaudio
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("⚠️  PyAudio non installé - Voice chat désactivé")
    print("   Pour activer: pip install pyaudio")

# Initialisation Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Couleurs
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 100, 255)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
YELLOW = (255, 255, 50)
CYAN = (0, 255, 255)
GRAY = (100, 100, 100)

# Couleurs arène
PURPLE = (138, 43, 226)
ORANGE = (255, 140, 0)
PINK = (255, 20, 147)
DARK_BLUE = (10, 10, 40)
NEON_BLUE = (0, 200, 255)
NEON_PURPLE = (180, 0, 255)
NEON_GREEN = (0, 255, 100)

# Taille de la map (plus grande que l'écran)
MAP_WIDTH = 2000
MAP_HEIGHT = 1500

COLOR_MAP = {
    "blue": BLUE,
    "red": RED,
    "green": GREEN,
    "yellow": YELLOW
}


class Spaceship:
    """Vaisseau spatial"""
    def __init__(self, player_id, x, y, color):
        self.id = player_id
        self.x = x
        self.y = y
        self.angle = 0
        self.vx = 0
        self.vy = 0
        self.health = 100
        self.color = COLOR_MAP.get(color, WHITE)
        self.size = 20
        self.name = f"Joueur{player_id}"
        self.spawn_protected = False  # Protection au spawn
        self.score = 0
        self.kills = 0
        self.deaths = 0
        self.is_dead = False
        
    def draw(self, screen, is_local=False):
        """Dessine le vaisseau"""
        # Triangle pointant dans la direction
        points = [
            (self.x + math.cos(self.angle) * self.size,
             self.y + math.sin(self.angle) * self.size),
            (self.x + math.cos(self.angle + 2.5) * self.size * 0.6,
             self.y + math.sin(self.angle + 2.5) * self.size * 0.6),
            (self.x + math.cos(self.angle - 2.5) * self.size * 0.6,
             self.y + math.sin(self.angle - 2.5) * self.size * 0.6)
        ]
        
        pygame.draw.polygon(screen, self.color, points)
        
        if is_local:
            pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), self.size + 5, 2)
        
        # Barre de santé
        bar_width = 40
        bar_height = 5
        bar_x = self.x - bar_width // 2
        bar_y = self.y - self.size - 15
        
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, bar_width * self.health / 100, bar_height))
        
        # Affiche le nom au-dessus du vaisseau
        font = pygame.font.Font(None, 20)
        name_text = font.render(self.name, True, WHITE)
        text_rect = name_text.get_rect(center=(self.x, self.y - self.size - 28))
        # Fond noir pour meilleure lisibilité
        pygame.draw.rect(screen, BLACK, text_rect.inflate(4, 2))
        screen.blit(name_text, text_rect)
        
    def update(self, data):
        """Met à jour depuis les données réseau"""
        self.x = data.get("x", self.x)
        self.y = data.get("y", self.y)
        self.angle = data.get("angle", self.angle)
        self.vx = data.get("vx", self.vx)
        self.vy = data.get("vy", self.vy)
        self.health = data.get("health", self.health)
        self.name = data.get("name", self.name)
        self.spawn_protected = data.get("spawn_protected", False)


class Laser:
    """Projectile laser"""
    def __init__(self, x, y, angle, owner_id, is_super=False):
        self.x = x
        self.y = y
        self.angle = angle
        self.is_super = is_super
        self.speed = 12 if is_super else 10
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.owner_id = owner_id
        self.lifetime = 150 if is_super else 120
        self.size = 8 if is_super else 3
        self.damage = 40 if is_super else 20
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        
    def draw(self, screen):
        # Super balle = plus grosse et orange
        if self.is_super:
            pygame.draw.circle(screen, ORANGE, (int(self.x), int(self.y)), self.size)
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.size - 3)
        else:
            pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), self.size)
        
    def is_dead(self):
        return (self.lifetime <= 0 or 
                self.x < 0 or self.x > MAP_WIDTH or
                self.y < 0 or self.y > MAP_HEIGHT)


class VoiceChat:
    """Gestion du chat vocal 🎤"""
    def __init__(self):
        self.audio = None
        self.chunk = 1024
        self.format = None
        self.channels = 1
        self.rate = 16000  # Qualité moyenne pour réduire la bande passante
        
        self.stream_in = None
        self.stream_out = None
        self.mic_active = False
        self.running = False
        self.available = VOICE_AVAILABLE
        
    def start(self):
        """Démarre les flux audio"""
        if not self.available:
            print("⚠️  Voice chat non disponible (PyAudio manquant)")
            return False
            
        try:
            self.audio = pyaudio.PyAudio()
            self.format = pyaudio.paInt16
            
            # Flux d'entrée (microphone)
            self.stream_in = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            # Flux de sortie (haut-parleurs)
            self.stream_out = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                output=True,
                frames_per_buffer=self.chunk
            )
            
            self.running = True
            print("🎤 Voice chat initialisé!")
            return True
        except Exception as e:
            print(f"⚠️  Erreur audio: {e}")
            self.available = False
            return False
    
    def capture_audio(self):
        """Capture un chunk audio du microphone"""
        if self.stream_in and self.mic_active and self.running:
            try:
                data = self.stream_in.read(self.chunk, exception_on_overflow=False)
                return base64.b64encode(data).decode('utf-8')
            except:
                pass
        return None
    
    def play_audio(self, encoded_data):
        """Joue un chunk audio reçu"""
        if self.stream_out and self.running:
            try:
                data = base64.b64decode(encoded_data)
                self.stream_out.write(data)
            except:
                pass
    
    def toggle_mic(self):
        """Active/désactive le micro"""
        if not self.available:
            print("⚠️  Voice chat non disponible")
            return False
        self.mic_active = not self.mic_active
        status = "🎤 ON" if self.mic_active else "🔇 OFF"
        print(f"Micro: {status}")
        return self.mic_active
    
    def stop(self):
        """Arrête les flux audio"""
        self.running = False
        self.mic_active = False
        if self.stream_in:
            try:
                self.stream_in.stop_stream()
                self.stream_in.close()
            except:
                pass
        if self.stream_out:
            try:
                self.stream_out.stop_stream()
                self.stream_out.close()
            except:
                pass
        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass


class SpaceArena:
    """Arène spatiale style Rocket League / Fortnite 🏟️"""
    
    def __init__(self):
        self.width = MAP_WIDTH
        self.height = MAP_HEIGHT
        
        # Étoiles de fond (positions fixes)
        self.stars = []
        for _ in range(200):
            self.stars.append({
                'x': random.randint(0, self.width),
                'y': random.randint(0, self.height),
                'size': random.randint(1, 3),
                'brightness': random.randint(100, 255),
                'twinkle_speed': random.uniform(0.02, 0.08)
            })
        
        # Nébuleuses (zones colorées)
        self.nebulas = []
        for _ in range(5):
            self.nebulas.append({
                'x': random.randint(100, self.width - 100),
                'y': random.randint(100, self.height - 100),
                'radius': random.randint(150, 400),
                'color': random.choice([PURPLE, PINK, NEON_BLUE, NEON_PURPLE]),
                'alpha': random.randint(20, 50)
            })
        
        # Astéroïdes (obstacles)
        self.asteroids = []
        for _ in range(12):
            self.asteroids.append({
                'x': random.randint(200, self.width - 200),
                'y': random.randint(200, self.height - 200),
                'radius': random.randint(30, 80),
                'rotation': random.uniform(0, 2 * math.pi),
                'rot_speed': random.uniform(-0.02, 0.02),
                'points': self._generate_asteroid_points(random.randint(6, 10))
            })
        
        # Zones de boost
        self.boost_zones = [
            {'x': 300, 'y': 300, 'radius': 50, 'color': NEON_GREEN, 'active': True, 'cooldown': 0},
            {'x': self.width - 300, 'y': 300, 'radius': 50, 'color': NEON_GREEN, 'active': True, 'cooldown': 0},
            {'x': 300, 'y': self.height - 300, 'radius': 50, 'color': NEON_GREEN, 'active': True, 'cooldown': 0},
            {'x': self.width - 300, 'y': self.height - 300, 'radius': 50, 'color': NEON_GREEN, 'active': True, 'cooldown': 0},
            {'x': self.width // 2, 'y': self.height // 2, 'radius': 70, 'color': ORANGE, 'active': True, 'cooldown': 0},
        ]
        
        self.time = 0
        
    def _generate_asteroid_points(self, num_points):
        """Génère des points irréguliers pour un astéroïde"""
        points = []
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            distance = random.uniform(0.7, 1.0)
            points.append((angle, distance))
        return points
    
    def update(self):
        """Met à jour les animations de l'arène"""
        self.time += 1
        
        # Rotation des astéroïdes
        for asteroid in self.asteroids:
            asteroid['rotation'] += asteroid['rot_speed']
        
        # Cooldown des zones de boost
        for zone in self.boost_zones:
            if not zone['active']:
                zone['cooldown'] -= 1
                if zone['cooldown'] <= 0:
                    zone['active'] = True
    
    def draw_background(self, screen, camera_x, camera_y):
        """Dessine le fond de l'arène"""
        # Fond dégradé spatial
        screen.fill(DARK_BLUE)
        
        # Nébuleuses (effet de glow)
        for nebula in self.nebulas:
            nx = nebula['x'] - camera_x
            ny = nebula['y'] - camera_y
            
            # Ne dessine que si visible
            if -nebula['radius'] < nx < SCREEN_WIDTH + nebula['radius'] and \
               -nebula['radius'] < ny < SCREEN_HEIGHT + nebula['radius']:
                # Plusieurs cercles concentriques pour l'effet de glow
                for i in range(5, 0, -1):
                    radius = int(nebula['radius'] * (i / 5))
                    alpha = nebula['alpha'] // i
                    color = (*nebula['color'][:3],)
                    # Surface avec alpha
                    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*color, alpha), (radius, radius), radius)
                    screen.blit(s, (nx - radius, ny - radius))
        
        # Étoiles avec scintillement
        for star in self.stars:
            sx = star['x'] - camera_x
            sy = star['y'] - camera_y
            
            # Wraparound pour les étoiles
            sx = sx % SCREEN_WIDTH
            sy = sy % SCREEN_HEIGHT
            
            # Scintillement
            twinkle = math.sin(self.time * star['twinkle_speed']) * 0.3 + 0.7
            brightness = int(star['brightness'] * twinkle)
            color = (brightness, brightness, brightness)
            
            pygame.draw.circle(screen, color, (int(sx), int(sy)), star['size'])
    
    def draw_arena(self, screen, camera_x, camera_y):
        """Dessine les éléments de l'arène"""
        
        # Grille de fond (style Tron)
        grid_spacing = 100
        grid_color = (30, 30, 80)
        
        # Lignes verticales
        start_x = int(-camera_x % grid_spacing)
        for x in range(start_x, SCREEN_WIDTH, grid_spacing):
            pygame.draw.line(screen, grid_color, (x, 0), (x, SCREEN_HEIGHT), 1)
        
        # Lignes horizontales
        start_y = int(-camera_y % grid_spacing)
        for y in range(start_y, SCREEN_HEIGHT, grid_spacing):
            pygame.draw.line(screen, grid_color, (0, y), (SCREEN_WIDTH, y), 1)
        
        # Zones de boost
        for zone in self.boost_zones:
            zx = zone['x'] - camera_x
            zy = zone['y'] - camera_y
            
            if -100 < zx < SCREEN_WIDTH + 100 and -100 < zy < SCREEN_HEIGHT + 100:
                if zone['active']:
                    # Effet pulsant
                    pulse = math.sin(self.time * 0.1) * 0.3 + 0.7
                    radius = int(zone['radius'] * pulse)
                    
                    # Cercles concentriques
                    for i in range(3, 0, -1):
                        r = radius + (i * 10)
                        alpha = 50 // i
                        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                        pygame.draw.circle(s, (*zone['color'], alpha), (r, r), r)
                        screen.blit(s, (zx - r, zy - r))
                    
                    pygame.draw.circle(screen, zone['color'], (int(zx), int(zy)), radius, 3)
                    
                    # Icône boost
                    font = pygame.font.Font(None, 24)
                    text = font.render("⚡", True, WHITE)
                    screen.blit(text, (zx - 8, zy - 10))
                else:
                    # Zone inactive (grisée)
                    pygame.draw.circle(screen, GRAY, (int(zx), int(zy)), zone['radius'], 2)
        
        # Astéroïdes
        for asteroid in self.asteroids:
            ax = asteroid['x'] - camera_x
            ay = asteroid['y'] - camera_y
            
            if -100 < ax < SCREEN_WIDTH + 100 and -100 < ay < SCREEN_HEIGHT + 100:
                # Dessine l'astéroïde avec ses points irréguliers
                points = []
                for angle, dist in asteroid['points']:
                    real_angle = angle + asteroid['rotation']
                    px = ax + math.cos(real_angle) * asteroid['radius'] * dist
                    py = ay + math.sin(real_angle) * asteroid['radius'] * dist
                    points.append((px, py))
                
                pygame.draw.polygon(screen, (80, 70, 60), points)
                pygame.draw.polygon(screen, (120, 110, 100), points, 3)
                
                # Cratères
                for i in range(3):
                    cx = ax + math.cos(asteroid['rotation'] + i * 2) * asteroid['radius'] * 0.4
                    cy = ay + math.sin(asteroid['rotation'] + i * 2) * asteroid['radius'] * 0.4
                    pygame.draw.circle(screen, (60, 50, 40), (int(cx), int(cy)), asteroid['radius'] // 6)
        
        # Murs de l'arène (style néon)
        wall_thickness = 5
        
        # Calcule les positions des murs par rapport à la caméra
        left = -camera_x
        top = -camera_y
        right = self.width - camera_x
        bottom = self.height - camera_y
        
        # Effet glow pour les murs
        for glow in range(3, 0, -1):
            glow_color = (NEON_BLUE[0] // glow, NEON_BLUE[1] // glow, NEON_BLUE[2] // glow)
            thickness = wall_thickness + glow * 4
            
            # Mur haut
            if 0 <= top <= SCREEN_HEIGHT:
                pygame.draw.line(screen, glow_color, (max(0, left), top), (min(SCREEN_WIDTH, right), top), thickness)
            # Mur bas
            if 0 <= bottom <= SCREEN_HEIGHT:
                pygame.draw.line(screen, glow_color, (max(0, left), bottom), (min(SCREEN_WIDTH, right), bottom), thickness)
            # Mur gauche
            if 0 <= left <= SCREEN_WIDTH:
                pygame.draw.line(screen, glow_color, (left, max(0, top)), (left, min(SCREEN_HEIGHT, bottom)), thickness)
            # Mur droit
            if 0 <= right <= SCREEN_WIDTH:
                pygame.draw.line(screen, glow_color, (right, max(0, top)), (right, min(SCREEN_HEIGHT, bottom)), thickness)
        
        # Coins lumineux
        corner_size = 30
        corners = [
            (left, top),
            (right, top),
            (left, bottom),
            (right, bottom)
        ]
        for cx, cy in corners:
            if -50 < cx < SCREEN_WIDTH + 50 and -50 < cy < SCREEN_HEIGHT + 50:
                pygame.draw.circle(screen, NEON_PURPLE, (int(cx), int(cy)), corner_size // 2)
                pygame.draw.circle(screen, WHITE, (int(cx), int(cy)), corner_size // 4)
    
    def draw_minimap(self, screen, player_x, player_y, other_players):
        """Dessine la minimap"""
        minimap_size = 150
        minimap_x = SCREEN_WIDTH - minimap_size - 10
        minimap_y = SCREEN_HEIGHT - minimap_size - 10
        
        # Fond de la minimap
        s = pygame.Surface((minimap_size, minimap_size), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 150), (0, 0, minimap_size, minimap_size))
        pygame.draw.rect(s, NEON_BLUE, (0, 0, minimap_size, minimap_size), 2)
        screen.blit(s, (minimap_x, minimap_y))
        
        # Ratio de conversion
        scale_x = minimap_size / self.width
        scale_y = minimap_size / self.height
        
        # Astéroïdes sur la minimap
        for asteroid in self.asteroids:
            ax = minimap_x + asteroid['x'] * scale_x
            ay = minimap_y + asteroid['y'] * scale_y
            pygame.draw.circle(screen, GRAY, (int(ax), int(ay)), 3)
        
        # Zones de boost sur la minimap
        for zone in self.boost_zones:
            if zone['active']:
                zx = minimap_x + zone['x'] * scale_x
                zy = minimap_y + zone['y'] * scale_y
                pygame.draw.circle(screen, zone['color'], (int(zx), int(zy)), 4)
        
        # Autres joueurs
        for ship in other_players.values():
            px = minimap_x + ship.x * scale_x
            py = minimap_y + ship.y * scale_y
            pygame.draw.circle(screen, ship.color, (int(px), int(py)), 4)
        
        # Joueur local (plus grand, avec contour)
        px = minimap_x + player_x * scale_x
        py = minimap_y + player_y * scale_y
        pygame.draw.circle(screen, WHITE, (int(px), int(py)), 6)
        pygame.draw.circle(screen, CYAN, (int(px), int(py)), 6, 2)
        
        # Label
        font = pygame.font.Font(None, 20)
        label = font.render("MINIMAP", True, NEON_BLUE)
        screen.blit(label, (minimap_x + 5, minimap_y + 5))
    
    def check_boost_collision(self, x, y):
        """Vérifie si le joueur touche une zone de boost"""
        for zone in self.boost_zones:
            if zone['active']:
                dist = math.sqrt((x - zone['x'])**2 + (y - zone['y'])**2)
                if dist < zone['radius']:
                    zone['active'] = False
                    zone['cooldown'] = 300  # 5 secondes à 60 FPS
                    return True
        return False
    
    def check_asteroid_collision(self, x, y, radius=20):
        """Vérifie collision avec un astéroïde"""
        for asteroid in self.asteroids:
            dist = math.sqrt((x - asteroid['x'])**2 + (y - asteroid['y'])**2)
            if dist < asteroid['radius'] + radius:
                return asteroid
        return None
    
    def clamp_position(self, x, y, margin=20):
        """Limite la position aux bords de l'arène"""
        x = max(margin, min(self.width - margin, x))
        y = max(margin, min(self.height - margin, y))
        return x, y


class SpaceBattleClient:
    """Client du jeu"""
    def __init__(self, server_ip, port=3500):
        self.server_ip = server_ip
        self.port = port
        self.socket = None
        self.running = False
        
        # Joueur local
        self.player_id = None
        self.local_ship = None
        
        # Autres joueurs
        self.other_ships = {}
        
        # Projectiles
        self.lasers = []
        
        # Pygame
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("🚀 Space Battle")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Voice chat
        self.voice_chat = VoiceChat()
        
        # Arène
        self.arena = SpaceArena()
        
        # Caméra (pour suivre le joueur)
        self.camera_x = 0
        self.camera_y = 0
        
        # Boost du joueur
        self.boost_amount = 0
        self.max_boost = 100
        self.is_boosting = False
        
        # Particules de flammes
        self.flame_particles = []
        
        # Protection au spawn (invincibilité)
        self.spawn_protection = True
        self.spawn_protection_timer = 180  # 3 secondes à 60 FPS
        self.spawn_protection_flash = 0
        
        # État de la partie
        self.current_round = 0
        self.total_rounds = 5
        self.time_remaining = 0
        self.round_active = False
        self.game_over = False
        
        # Super balle
        self.super_bullet_available = False
        self.super_bullet_used = False
        self.super_bullet_flash = 0
        self.super_bullet_armed = False  # True quand E est pressé
        
        # Pickups de santé
        self.health_pickups = {}
        
        # État du joueur
        self.is_dead = False
        self.respawn_timer = 0
        
        # Scores
        self.scores = {}
        
    def connect(self):
        """Se connecte au serveur"""
        try:
            print(f"🔄 Connexion à {self.server_ip}:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # Timeout de 5 secondes
            self.socket.connect((self.server_ip, self.port))
            print("✅ Socket connecté!")
            
            # Reçoit le message de bienvenue
            print("⏳ Attente du message de bienvenue...")
            data = self.socket.recv(4096)
            print(f"📦 Reçu {len(data)} bytes")
            
            # Enlève le timeout après la connexion
            self.socket.settimeout(None)
            
            # Parse le message (peut avoir un \n à la fin)
            message_str = data.decode().strip()
            welcome = json.loads(message_str)
            
            if welcome.get("type") == "welcome":
                self.player_id = welcome["player_id"]
                color = welcome["color"]
                
                # Demande le nom au joueur
                print(f"\n👤 Vous êtes le Joueur {self.player_id} ({color})")
                player_name = input("   Entrez votre nom (ou Entrée pour nom par défaut): ").strip()
                
                if not player_name:
                    player_name = f"Joueur{self.player_id}"
                
                # Limite à 20 caractères
                player_name = player_name[:20]
                
                # Envoie le nom au serveur
                name_msg = {
                    "type": "set_name",
                    "name": player_name
                }
                self.send_message(name_msg)
                
                self.local_ship = Spaceship(
                    self.player_id,
                    MAP_WIDTH // 2,
                    MAP_HEIGHT // 2,
                    color
                )
                self.local_ship.name = player_name
                
                print(f"✅ Connecté en tant que '{player_name}'!")
                return True
            else:
                print(f"❌ {welcome.get('error', 'Erreur de connexion')}")
                return False
                
        except socket.timeout:
            print("❌ Timeout: Le serveur ne répond pas assez vite")
            return False
        except ConnectionRefusedError:
            print("❌ Connexion refusée: Le serveur n'est pas lancé ou le port est bloqué")
            return False
        except Exception as e:
            print(f"❌ Impossible de se connecter: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self):
        """Démarre le jeu"""
        print("🎮 Démarrage du client...")
        
        if not self.connect():
            print("❌ Échec de connexion. Fermeture...")
            pygame.quit()
            return
        
        print("✅ Connexion réussie! Démarrage du jeu...")
        self.running = True
        
        # Initialise le voice chat
        self.voice_chat.start()
        
        # Thread pour recevoir les messages
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()
        
        # Thread pour envoyer l'audio
        voice_thread = threading.Thread(target=self.voice_send_loop, daemon=True)
        voice_thread.start()
        
        print("🎮 Lancement de la boucle de jeu...")
        
        # Boucle de jeu
        try:
            self.game_loop()
        except Exception as e:
            print(f"❌ Erreur dans la boucle de jeu: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    def receive_messages(self):
        """Reçoit les messages du serveur"""
        buffer = ""
        print("📡 Thread de réception démarré")
        
        while self.running:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    print("📡 Connexion fermée par le serveur")
                    break
                
                buffer += data
                
                # Traite chaque ligne (message) séparément
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            self.process_message(message)
                        except json.JSONDecodeError as e:
                            print(f"⚠️  JSON invalide: {e}")
                            print(f"   Données: {line[:100]}")
                            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️  Erreur réception: {e}")
                break
        
        print("📡 Thread de réception arrêté")
        self.running = False
    
    def voice_send_loop(self):
        """Envoie l'audio du micro en continu"""
        while self.running and self.voice_chat.running:
            audio_data = self.voice_chat.capture_audio()
            if audio_data:
                voice_msg = {
                    "type": "voice",
                    "audio": audio_data
                }
                self.send_message(voice_msg)
            time.sleep(0.05)  # ~20 packets par seconde
    
    def process_message(self, message):
        """Traite un message du serveur"""
        msg_type = message.get("type")
        
        if msg_type == "game_state":
            # Met à jour l'état de la partie
            self.current_round = message.get("round", 0)
            self.total_rounds = message.get("total_rounds", 5)
            self.time_remaining = message.get("time_remaining", 0)
            self.round_active = message.get("round_active", False)
            self.game_over = message.get("game_over", False)
            self.super_bullet_available = message.get("super_bullet_available", False)
            
            # Met à jour les pickups
            self.health_pickups = {}
            for pickup_data in message.get("health_pickups", []):
                self.health_pickups[pickup_data["id"]] = pickup_data
            
            # Met à jour tous les joueurs
            for player_data in message.get("players", []):
                player_id = player_data["id"]
                
                if player_id == self.player_id:
                    # Mise à jour locale
                    self.local_ship.health = player_data.get("health", self.local_ship.health)
                    self.local_ship.score = player_data.get("score", 0)
                    self.local_ship.kills = player_data.get("kills", 0)
                    self.local_ship.deaths = player_data.get("deaths", 0)
                    
                    # Gestion de la mort/respawn
                    was_dead = self.is_dead
                    self.is_dead = player_data.get("is_dead", False)
                    
                    if self.is_dead and not was_dead:
                        self.respawn_timer = 180  # 3 secondes
                        print("💀 Vous avez été éliminé! Respawn dans 3s...")
                    elif not self.is_dead and was_dead:
                        # On vient de respawn
                        self.spawn_protection = True
                        self.spawn_protection_timer = 180
                        self.local_ship.x = player_data.get("x", self.local_ship.x)
                        self.local_ship.y = player_data.get("y", self.local_ship.y)
                        print("🔄 Vous êtes de retour!")
                else:
                    # Autres joueurs
                    if player_id not in self.other_ships:
                        self.other_ships[player_id] = Spaceship(
                            player_id,
                            player_data["x"],
                            player_data["y"],
                            player_data["color"]
                        )
                        self.other_ships[player_id].name = player_data.get("name", f"Joueur{player_id}")
                    
                        self.other_ships[player_id].update(player_data)
                    self.other_ships[player_id].is_dead = player_data.get("is_dead", False)
                    self.other_ships[player_id].score = player_data.get("score", 0)
                    self.other_ships[player_id].kills = player_data.get("kills", 0)
            
            # Supprime les joueurs partis
            current_ids = {p["id"] for p in message.get("players", [])}
            for player_id in list(self.other_ships.keys()):
                if player_id not in current_ids:
                    del self.other_ships[player_id]
                    
        elif msg_type == "player_shoot":
            # Un autre joueur a tiré
            player_id = message["player_id"]
            if player_id != self.player_id:
                laser = Laser(
                    message["x"],
                    message["y"],
                    message["angle"],
                    player_id
                )
                self.lasers.append(laser)
        
        elif msg_type == "player_left":
            player_id = message["player_id"]
            if player_id in self.other_ships:
                del self.other_ships[player_id]
        
        elif msg_type == "voice":
            # Réception audio d'un autre joueur
            player_id = message.get("player_id")
            if player_id != self.player_id:
                audio_data = message.get("audio")
                if audio_data:
                    self.voice_chat.play_audio(audio_data)
        
        elif msg_type == "round_start":
            round_num = message.get("round", 1)
            print(f"\n🏁 MANCHE {round_num}/{self.total_rounds} DÉMARRÉE!")
            self.super_bullet_used = False
        
        elif msg_type == "round_end":
            round_num = message.get("round", 1)
            print(f"\n🏁 MANCHE {round_num} TERMINÉE!")
        
        elif msg_type == "game_over":
            winner = message.get("winner", "Inconnu")
            print(f"\n🏆 PARTIE TERMINÉE! Gagnant: {winner}")
        
        elif msg_type == "super_bullet_available":
            if not self.super_bullet_used:
                print("💥 SUPER BALLE DISPONIBLE! (Prochain tir)")
                self.super_bullet_flash = 60
        
        elif msg_type == "pickup_spawn":
            pickup = message.get("pickup")
            if pickup:
                self.health_pickups[pickup["id"]] = pickup
                print(f"💉 Pickup de santé apparu!")
        
        elif msg_type == "pickup_collected":
            pickup_id = message.get("pickup_id")
            if pickup_id in self.health_pickups:
                del self.health_pickups[pickup_id]
    
    def handle_input(self):
        """Gère les entrées joueur"""
        # Ne peut pas bouger si mort
        if self.is_dead:
            return
        
        keys = pygame.key.get_pressed()
        
        # Rotation avec souris (convertir en coordonnées monde)
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # La position du vaisseau sur l'écran
        ship_screen_x = self.local_ship.x - self.camera_x
        ship_screen_y = self.local_ship.y - self.camera_y
        dx = mouse_x - ship_screen_x
        dy = mouse_y - ship_screen_y
        self.local_ship.angle = math.atan2(dy, dx)
        
        # Mouvement
        accel = 0.5
        friction = 0.95
        
        if keys[pygame.K_w] or keys[pygame.K_z]:  # Avant
            self.local_ship.vx += math.cos(self.local_ship.angle) * accel
            self.local_ship.vy += math.sin(self.local_ship.angle) * accel
        if keys[pygame.K_s]:  # Arrière
            self.local_ship.vx -= math.cos(self.local_ship.angle) * accel * 0.5
            self.local_ship.vy -= math.sin(self.local_ship.angle) * accel * 0.5
        if keys[pygame.K_a] or keys[pygame.K_q]:  # Gauche
            angle_left = self.local_ship.angle - math.pi / 2
            self.local_ship.vx += math.cos(angle_left) * accel * 0.7
            self.local_ship.vy += math.sin(angle_left) * accel * 0.7
        if keys[pygame.K_d]:  # Droite
            angle_right = self.local_ship.angle + math.pi / 2
            self.local_ship.vx += math.cos(angle_right) * accel * 0.7
            self.local_ship.vy += math.sin(angle_right) * accel * 0.7
        
        # Friction
        self.local_ship.vx *= friction
        self.local_ship.vy *= friction
        
        # Utilise le boost avec SHIFT (AVANT la limite de vitesse!)
        self.is_boosting = False
        if keys[pygame.K_LSHIFT] and self.boost_amount > 0:
            boost_power = 1.2
            self.local_ship.vx += math.cos(self.local_ship.angle) * boost_power
            self.local_ship.vy += math.sin(self.local_ship.angle) * boost_power
            self.boost_amount -= 0.5  # Consomme moins vite
            self.is_boosting = True
            
            # Génère des particules de flammes
            for _ in range(3):
                # Position derrière le vaisseau
                back_angle = self.local_ship.angle + math.pi
                offset_x = math.cos(back_angle) * 15 + random.uniform(-5, 5)
                offset_y = math.sin(back_angle) * 15 + random.uniform(-5, 5)
                
                self.flame_particles.append({
                    'x': self.local_ship.x + offset_x,
                    'y': self.local_ship.y + offset_y,
                    'vx': math.cos(back_angle) * random.uniform(2, 5) + self.local_ship.vx * 0.3,
                    'vy': math.sin(back_angle) * random.uniform(2, 5) + self.local_ship.vy * 0.3,
                    'life': random.randint(10, 25),
                    'max_life': 25,
                    'size': random.uniform(4, 10),
                    'color_type': random.choice(['orange', 'yellow', 'red'])
                })
        
        # Limite vitesse (plus haute si boost actif)
        max_speed = 15 if self.is_boosting else 8
        speed = math.sqrt(self.local_ship.vx**2 + self.local_ship.vy**2)
        if speed > max_speed:
            self.local_ship.vx = (self.local_ship.vx / speed) * max_speed
            self.local_ship.vy = (self.local_ship.vy / speed) * max_speed
        
        # Position
        self.local_ship.x += self.local_ship.vx
        self.local_ship.y += self.local_ship.vy
        
        # Met à jour les particules de flammes
        self.update_flame_particles()
        
        # Collision avec astéroïdes
        asteroid = self.arena.check_asteroid_collision(self.local_ship.x, self.local_ship.y)
        if asteroid:
            # Rebond
            dx = self.local_ship.x - asteroid['x']
            dy = self.local_ship.y - asteroid['y']
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 0:
                # Pousse le joueur hors de l'astéroïde
                push_dist = asteroid['radius'] + 25 - dist
                self.local_ship.x += (dx / dist) * push_dist
                self.local_ship.y += (dy / dist) * push_dist
                # Inverse la vélocité
                self.local_ship.vx *= -0.5
                self.local_ship.vy *= -0.5
        
        # Limite aux bords de l'arène (au lieu de wraparound)
        self.local_ship.x, self.local_ship.y = self.arena.clamp_position(
            self.local_ship.x, self.local_ship.y
        )
        
        # Collecte de boost
        if self.arena.check_boost_collision(self.local_ship.x, self.local_ship.y):
            self.boost_amount = min(self.max_boost, self.boost_amount + 30)
            print("⚡ Boost collecté!")
        
        # Collecte de pickup de santé
        for pickup_id, pickup in list(self.health_pickups.items()):
            dist = math.sqrt((self.local_ship.x - pickup["x"])**2 + 
                           (self.local_ship.y - pickup["y"])**2)
            if dist < 40:  # Rayon de collecte
                self.send_message({
                    "type": "pickup_collect",
                    "pickup_id": pickup_id
                })
                print("💉 Soin collecté! +50 HP")
                if pickup_id in self.health_pickups:
                    del self.health_pickups[pickup_id]
                break
    
    def update_flame_particles(self):
        """Met à jour les particules de flammes"""
        particles_to_remove = []
        
        for particle in self.flame_particles:
            # Mouvement
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            
            # Ralentit
            particle['vx'] *= 0.92
            particle['vy'] *= 0.92
            
            # Réduit la taille
            particle['size'] *= 0.95
            
            # Vie
            particle['life'] -= 1
            
            if particle['life'] <= 0 or particle['size'] < 1:
                particles_to_remove.append(particle)
        
        for particle in particles_to_remove:
            self.flame_particles.remove(particle)
        
        # Limite le nombre de particules
        if len(self.flame_particles) > 100:
            self.flame_particles = self.flame_particles[-100:]
    
    def shoot(self):
        """Tire un laser"""
        # Vérifie si c'est une super balle (doit être armée avec E)
        is_super = self.super_bullet_available and not self.super_bullet_used and self.super_bullet_armed
        
        if is_super:
            self.super_bullet_used = True
            self.super_bullet_armed = False
            print("💥 SUPER BALLE TIRÉE!")
        
        laser = Laser(
            self.local_ship.x,
            self.local_ship.y,
            self.local_ship.angle,
            self.player_id,
            is_super=is_super
        )
        self.lasers.append(laser)
        
        # Envoie au serveur
        shoot_msg = {
            "type": "shoot",
            "x": self.local_ship.x,
            "y": self.local_ship.y,
            "angle": self.local_ship.angle,
            "is_super": is_super
        }
        self.send_message(shoot_msg)
    
    def update_lasers(self):
        """Met à jour les lasers"""
        lasers_to_remove = []
        
        for laser in self.lasers:
            laser.update()
            
            hit = False
            # Vérifie collisions (ignore les joueurs morts)
            if laser.owner_id == self.player_id:
                for ship in self.other_ships.values():
                    if ship.is_dead:
                        continue
                    dist = math.sqrt((laser.x - ship.x)**2 + (laser.y - ship.y)**2)
                    if dist < ship.size + laser.size:  # Taille du laser compte
                        # Hit!
                        self.send_message({
                            "type": "hit",
                            "target_id": ship.id,
                            "damage": laser.damage,
                            "is_super": laser.is_super
                        })
                        lasers_to_remove.append(laser)
                        hit = True
                        break
            
            if not hit and laser.is_dead():
                lasers_to_remove.append(laser)
        
        # Supprime les lasers marqués
        for laser in lasers_to_remove:
            if laser in self.lasers:
                self.lasers.remove(laser)
    
    def send_position(self):
        """Envoie la position au serveur"""
        move_msg = {
            "type": "move",
            "x": self.local_ship.x,
            "y": self.local_ship.y,
            "angle": self.local_ship.angle,
            "vx": self.local_ship.vx,
            "vy": self.local_ship.vy
        }
        self.send_message(move_msg)
    
    def send_message(self, message):
        """Envoie un message au serveur"""
        try:
            data = (json.dumps(message) + '\n').encode()
            self.socket.send(data)
        except Exception as e:
            print(f"⚠️  Erreur envoi: {e}")
            self.running = False
    
    def update_camera(self):
        """Met à jour la caméra pour suivre le joueur"""
        # Centre la caméra sur le joueur
        target_x = self.local_ship.x - SCREEN_WIDTH // 2
        target_y = self.local_ship.y - SCREEN_HEIGHT // 2
        
        # Lissage de la caméra
        self.camera_x += (target_x - self.camera_x) * 0.1
        self.camera_y += (target_y - self.camera_y) * 0.1
        
        # Limite la caméra aux bords de la map
        self.camera_x = max(0, min(MAP_WIDTH - SCREEN_WIDTH, self.camera_x))
        self.camera_y = max(0, min(MAP_HEIGHT - SCREEN_HEIGHT, self.camera_y))
    
    def draw(self):
        """Dessine tout"""
        # Fond de l'arène
        self.arena.draw_background(self.screen, self.camera_x, self.camera_y)
        
        # Éléments de l'arène (grille, murs, obstacles)
        self.arena.draw_arena(self.screen, self.camera_x, self.camera_y)
        
        # Particules de flammes (boost) 🔥
        for particle in self.flame_particles:
            px = particle['x'] - self.camera_x
            py = particle['y'] - self.camera_y
            
            if 0 <= px <= SCREEN_WIDTH and 0 <= py <= SCREEN_HEIGHT:
                # Couleur selon le type et la vie restante
                life_ratio = particle['life'] / particle['max_life']
                
                if particle['color_type'] == 'orange':
                    color = (255, int(140 * life_ratio), 0)
                elif particle['color_type'] == 'yellow':
                    color = (255, int(255 * life_ratio), 0)
                else:  # red
                    color = (255, int(50 * life_ratio), 0)
                
                size = int(particle['size'])
                if size > 0:
                    # Dessine avec un effet de glow
                    glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (*color, int(100 * life_ratio)), 
                                      (size * 2, size * 2), size * 2)
                    pygame.draw.circle(glow_surf, (*color, int(200 * life_ratio)), 
                                      (size * 2, size * 2), size)
                    self.screen.blit(glow_surf, (px - size * 2, py - size * 2))
        
        # Lasers
        for laser in self.lasers:
            lx = laser.x - self.camera_x
            ly = laser.y - self.camera_y
            if 0 <= lx <= SCREEN_WIDTH and 0 <= ly <= SCREEN_HEIGHT:
                pygame.draw.circle(self.screen, CYAN, (int(lx), int(ly)), 3)
                # Trainée du laser
                trail_x = lx - laser.vx * 2
                trail_y = ly - laser.vy * 2
                pygame.draw.line(self.screen, (0, 150, 200), (int(trail_x), int(trail_y)), (int(lx), int(ly)), 2)
        
        # Pickups de santé (seringues)
        for pickup in self.health_pickups.values():
            px = pickup["x"] - self.camera_x
            py = pickup["y"] - self.camera_y
            if -50 < px < SCREEN_WIDTH + 50 and -50 < py < SCREEN_HEIGHT + 50:
                # Effet pulsant
                pulse = math.sin(pygame.time.get_ticks() * 0.005) * 0.2 + 1.0
                size = int(20 * pulse)
                
                # Glow vert
                glow_surf = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (0, 255, 100, 50), (size * 1.5, size * 1.5), size * 1.5)
                self.screen.blit(glow_surf, (px - size * 1.5, py - size * 1.5))
                
                # Croix médicale
                pygame.draw.rect(self.screen, (255, 255, 255), (px - 3, py - 12, 6, 24))
                pygame.draw.rect(self.screen, (255, 255, 255), (px - 12, py - 3, 24, 6))
                pygame.draw.rect(self.screen, (0, 200, 100), (px - 2, py - 10, 4, 20))
                pygame.draw.rect(self.screen, (0, 200, 100), (px - 10, py - 2, 20, 4))
                
                # Label
                font = pygame.font.Font(None, 18)
                label = font.render("+50", True, NEON_GREEN)
                self.screen.blit(label, (px - 12, py + 18))
        
        # Vaisseaux des autres joueurs (seulement s'ils sont vivants)
        for ship in self.other_ships.values():
            if ship.is_dead:
                continue  # Ne pas dessiner les joueurs morts
            sx = ship.x - self.camera_x
            sy = ship.y - self.camera_y
            if -50 < sx < SCREEN_WIDTH + 50 and -50 < sy < SCREEN_HEIGHT + 50:
                self._draw_ship(ship, sx, sy, is_local=False)
        
        # Vaisseau local (seulement si vivant)
        if self.local_ship and not self.is_dead:
            lx = self.local_ship.x - self.camera_x
            ly = self.local_ship.y - self.camera_y
            self._draw_ship(self.local_ship, lx, ly, is_local=True)
        
        # Minimap
        self.arena.draw_minimap(
            self.screen, 
            self.local_ship.x, 
            self.local_ship.y, 
            self.other_ships
        )
        
        # HUD
        self._draw_hud()
        
        # Réticule
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.circle(self.screen, RED, mouse_pos, 10, 2)
        pygame.draw.line(self.screen, RED, (mouse_pos[0] - 15, mouse_pos[1]), (mouse_pos[0] + 15, mouse_pos[1]), 2)
        pygame.draw.line(self.screen, RED, (mouse_pos[0], mouse_pos[1] - 15), (mouse_pos[0], mouse_pos[1] + 15), 2)
        
        pygame.display.flip()
    
    def _draw_ship(self, ship, screen_x, screen_y, is_local=False):
        """Dessine un vaisseau à une position écran"""
        
        # Détermine si ce vaisseau est protégé
        is_protected = (is_local and self.spawn_protection) or (not is_local and ship.spawn_protected)
        
        # Effet de protection au spawn (bouclier)
        if is_protected:
            # Animation du bouclier
            if is_local:
                shield_pulse = math.sin(self.spawn_protection_flash * 0.2) * 0.3 + 0.7
                flash_value = self.spawn_protection_flash
            else:
                # Pour les autres joueurs, utilise le temps global
                flash_value = pygame.time.get_ticks() // 16
                shield_pulse = math.sin(flash_value * 0.2) * 0.3 + 0.7
            
            shield_radius = int((ship.size + 20) * shield_pulse)
            
            # Bouclier stylisé
            shield_surface = pygame.Surface((shield_radius * 2 + 20, shield_radius * 2 + 20), pygame.SRCALPHA)
            
            # Cercles concentriques pour l'effet de bouclier
            for i in range(3):
                alpha = int(80 - i * 20)
                radius = shield_radius - i * 5
                color = (100, 200, 255, alpha)  # Bleu clair
                pygame.draw.circle(shield_surface, color, (shield_radius + 10, shield_radius + 10), radius, 3)
            
            # Remplissage semi-transparent
            pygame.draw.circle(shield_surface, (100, 200, 255, 30), (shield_radius + 10, shield_radius + 10), shield_radius)
            
            self.screen.blit(shield_surface, (screen_x - shield_radius - 10, screen_y - shield_radius - 10))
            
            # Texte du compte à rebours (seulement pour le joueur local)
            if is_local:
                seconds_left = (self.spawn_protection_timer // 60) + 1
                font = pygame.font.Font(None, 28)
                timer_text = font.render(f"🛡️ {seconds_left}s", True, (100, 200, 255))
                text_rect = timer_text.get_rect(center=(screen_x, screen_y - ship.size - 45))
                self.screen.blit(timer_text, text_rect)
            else:
                # Indicateur "PROTÉGÉ" pour les autres joueurs
                font = pygame.font.Font(None, 20)
                prot_text = font.render("🛡️", True, (100, 200, 255))
                text_rect = prot_text.get_rect(center=(screen_x, screen_y - ship.size - 45))
                self.screen.blit(prot_text, text_rect)
        
        # Triangle
        points = [
            (screen_x + math.cos(ship.angle) * ship.size,
             screen_y + math.sin(ship.angle) * ship.size),
            (screen_x + math.cos(ship.angle + 2.5) * ship.size * 0.6,
             screen_y + math.sin(ship.angle + 2.5) * ship.size * 0.6),
            (screen_x + math.cos(ship.angle - 2.5) * ship.size * 0.6,
             screen_y + math.sin(ship.angle - 2.5) * ship.size * 0.6)
        ]
        
        # Effet boost (flammes à l'arrière du vaisseau)
        if is_local and self.is_boosting:
            back_angle = ship.angle + math.pi
            flame_length = 25 + random.randint(0, 15)
            
            # Points de la flamme (triangle qui sort de l'arrière)
            flame_points = [
                (screen_x + math.cos(back_angle + 0.3) * ship.size * 0.4,
                 screen_y + math.sin(back_angle + 0.3) * ship.size * 0.4),
                (screen_x + math.cos(back_angle - 0.3) * ship.size * 0.4,
                 screen_y + math.sin(back_angle - 0.3) * ship.size * 0.4),
                (screen_x + math.cos(back_angle) * flame_length,
                 screen_y + math.sin(back_angle) * flame_length)
            ]
            
            # Dessine plusieurs couches de flamme
            # Orange externe
            pygame.draw.polygon(self.screen, ORANGE, flame_points)
            
            # Jaune interne
            inner_length = flame_length * 0.7
            inner_points = [
                (screen_x + math.cos(back_angle + 0.2) * ship.size * 0.3,
                 screen_y + math.sin(back_angle + 0.2) * ship.size * 0.3),
                (screen_x + math.cos(back_angle - 0.2) * ship.size * 0.3,
                 screen_y + math.sin(back_angle - 0.2) * ship.size * 0.3),
                (screen_x + math.cos(back_angle) * inner_length,
                 screen_y + math.sin(back_angle) * inner_length)
            ]
            pygame.draw.polygon(self.screen, YELLOW, inner_points)
            
            # Blanc au centre
            core_length = flame_length * 0.4
            core_points = [
                (screen_x + math.cos(back_angle + 0.1) * ship.size * 0.2,
                 screen_y + math.sin(back_angle + 0.1) * ship.size * 0.2),
                (screen_x + math.cos(back_angle - 0.1) * ship.size * 0.2,
                 screen_y + math.sin(back_angle - 0.1) * ship.size * 0.2),
                (screen_x + math.cos(back_angle) * core_length,
                 screen_y + math.sin(back_angle) * core_length)
            ]
            pygame.draw.polygon(self.screen, WHITE, core_points)
        
        # Effet glow pour le vaisseau local
        if is_local:
            glow_color = ORANGE if self.is_boosting else CYAN
            glow_surface = pygame.Surface((ship.size * 4, ship.size * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (*glow_color[:3], 50), (ship.size * 2, ship.size * 2), ship.size + 10)
            self.screen.blit(glow_surface, (screen_x - ship.size * 2, screen_y - ship.size * 2))
        
        pygame.draw.polygon(self.screen, ship.color, points)
        pygame.draw.polygon(self.screen, WHITE, points, 2)
        
        if is_local:
            ring_color = ORANGE if self.is_boosting else CYAN
            pygame.draw.circle(self.screen, ring_color, (int(screen_x), int(screen_y)), ship.size + 5, 2)
        
        # Barre de santé
        bar_width = 40
        bar_height = 5
        bar_x = screen_x - bar_width // 2
        bar_y = screen_y - ship.size - 15
        
        pygame.draw.rect(self.screen, RED, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(self.screen, GREEN, (bar_x, bar_y, bar_width * ship.health / 100, bar_height))
        
        # Nom
        font = pygame.font.Font(None, 20)
        name_text = font.render(ship.name, True, WHITE)
        text_rect = name_text.get_rect(center=(screen_x, screen_y - ship.size - 28))
        pygame.draw.rect(self.screen, BLACK, text_rect.inflate(4, 2))
        self.screen.blit(name_text, text_rect)
    
    def _draw_hud(self):
        """Dessine le HUD"""
        # ═══════════════════════════════════════════════════
        # PANNEAU SUPÉRIEUR CENTRAL - Round et Timer
        # ═══════════════════════════════════════════════════
        
        # Fond du panneau
        panel_width = 250
        panel_x = SCREEN_WIDTH // 2 - panel_width // 2
        pygame.draw.rect(self.screen, (0, 0, 0, 180), (panel_x, 5, panel_width, 50))
        pygame.draw.rect(self.screen, NEON_BLUE, (panel_x, 5, panel_width, 50), 2)
        
        # Manche
        round_text = self.font.render(f"MANCHE {self.current_round}/{self.total_rounds}", True, WHITE)
        round_rect = round_text.get_rect(center=(SCREEN_WIDTH // 2, 20))
        self.screen.blit(round_text, round_rect)
        
        # Timer
        minutes = int(self.time_remaining // 60)
        seconds = int(self.time_remaining % 60)
        timer_color = RED if self.time_remaining < 30 else YELLOW if self.time_remaining < 60 else WHITE
        timer_text = self.font.render(f"{minutes:02d}:{seconds:02d}", True, timer_color)
        timer_rect = timer_text.get_rect(center=(SCREEN_WIDTH // 2, 42))
        self.screen.blit(timer_text, timer_rect)
        
        # ═══════════════════════════════════════════════════
        # PANNEAU GAUCHE - Stats du joueur
        # ═══════════════════════════════════════════════════
        
        y_offset = 10
        
        # Nom et santé
        info_text = self.small_font.render(f"{self.local_ship.name}", True, WHITE)
        self.screen.blit(info_text, (10, y_offset))
        y_offset += 20
        
        # Barre de santé
        health_bar_width = 150
        health_bar_height = 12
        pygame.draw.rect(self.screen, (50, 50, 50), (10, y_offset, health_bar_width, health_bar_height))
        health_fill = (self.local_ship.health / 100) * health_bar_width
        health_color = GREEN if self.local_ship.health > 50 else YELLOW if self.local_ship.health > 25 else RED
        pygame.draw.rect(self.screen, health_color, (10, y_offset, health_fill, health_bar_height))
        pygame.draw.rect(self.screen, WHITE, (10, y_offset, health_bar_width, health_bar_height), 1)
        
        health_label = self.small_font.render(f"{int(self.local_ship.health)}/100", True, WHITE)
        self.screen.blit(health_label, (165, y_offset - 2))
        y_offset += 20
        
        # Kills et Score
        kills_text = self.small_font.render(f"🎯 Kills: {self.local_ship.kills}", True, WHITE)
        self.screen.blit(kills_text, (10, y_offset))
        y_offset += 18
        
        score_text = self.small_font.render(f"⭐ Score: {self.local_ship.score}", True, YELLOW)
        self.screen.blit(score_text, (10, y_offset))
        y_offset += 25
        
        # Barre de boost
        boost_bar_width = 150
        boost_bar_height = 12
        pygame.draw.rect(self.screen, (30, 30, 30), (10, y_offset, boost_bar_width, boost_bar_height))
        fill_width = (self.boost_amount / self.max_boost) * boost_bar_width
        boost_color = NEON_GREEN if self.boost_amount > 30 else ORANGE if self.boost_amount > 10 else RED
        pygame.draw.rect(self.screen, boost_color, (10, y_offset, fill_width, boost_bar_height))
        pygame.draw.rect(self.screen, WHITE, (10, y_offset, boost_bar_width, boost_bar_height), 1)
        boost_label = self.small_font.render(f"⚡ BOOST (SHIFT)", True, WHITE)
        self.screen.blit(boost_label, (10, y_offset - 15))
        y_offset += 20
        
        # Super balle disponible
        if self.super_bullet_available and not self.super_bullet_used:
            self.super_bullet_flash = (self.super_bullet_flash + 1) % 30
            
            if self.super_bullet_armed:
                # Super balle armée - prête à tirer
                pygame.draw.rect(self.screen, (255, 50, 0), (5, y_offset - 2, 200, 22))
                pygame.draw.rect(self.screen, YELLOW, (5, y_offset - 2, 200, 22), 2)
                super_text = self.small_font.render("💥 ARMÉE! TIREZ!", True, WHITE)
                self.screen.blit(super_text, (10, y_offset))
            else:
                # Super balle disponible - appuyer sur E
                if self.super_bullet_flash < 20:
                    pygame.draw.rect(self.screen, (100, 50, 0), (5, y_offset - 2, 200, 22))
                    super_text = self.small_font.render("💥 SUPER BALLE [E]", True, ORANGE)
                    self.screen.blit(super_text, (10, y_offset))
        y_offset += 25
        
        # Indicateur micro
        if self.voice_chat.available:
            mic_status = "🎤 ON" if self.voice_chat.mic_active else "🔇 OFF"
            mic_color = GREEN if self.voice_chat.mic_active else RED
            mic_text = self.small_font.render(f"Micro: {mic_status} (V)", True, mic_color)
            self.screen.blit(mic_text, (10, y_offset))
        
        # ═══════════════════════════════════════════════════
        # PANNEAU DROIT - Tableau des scores
        # ═══════════════════════════════════════════════════
        
        # Liste tous les joueurs triés par score
        all_players = [(self.local_ship.name, self.local_ship.score, self.local_ship.kills, True)]
        for ship in self.other_ships.values():
            all_players.append((ship.name, ship.score, ship.kills, False))
        all_players.sort(key=lambda x: x[1], reverse=True)
        
        scoreboard_x = SCREEN_WIDTH - 220
        scoreboard_y = 60
        scoreboard_width = 210
        row_height = 28
        num_players = min(len(all_players), 6)
        scoreboard_height = 35 + num_players * row_height
        
        # Fond du tableau
        pygame.draw.rect(self.screen, (0, 0, 0, 200), (scoreboard_x - 5, scoreboard_y - 5, scoreboard_width, scoreboard_height))
        pygame.draw.rect(self.screen, NEON_PURPLE, (scoreboard_x - 5, scoreboard_y - 5, scoreboard_width, scoreboard_height), 3)
        
        # Titre avec ligne de séparation
        title = self.font.render("🏆 SCORES", True, YELLOW)
        title_rect = title.get_rect(center=(scoreboard_x + scoreboard_width // 2 - 5, scoreboard_y + 12))
        self.screen.blit(title, title_rect)
        scoreboard_y += 30
        
        # Ligne de séparation sous le titre
        pygame.draw.line(self.screen, NEON_PURPLE, 
                        (scoreboard_x, scoreboard_y - 5), 
                        (scoreboard_x + scoreboard_width - 10, scoreboard_y - 5), 2)
        
        # En-têtes des colonnes
        header_font = pygame.font.Font(None, 18)
        pygame.draw.rect(self.screen, (30, 30, 60), (scoreboard_x, scoreboard_y, scoreboard_width - 10, 20))
        
        rank_header = header_font.render("#", True, GRAY)
        name_header = header_font.render("JOUEUR", True, GRAY)
        kills_header = header_font.render("KILLS", True, GRAY)
        score_header = header_font.render("PTS", True, GRAY)
        
        self.screen.blit(rank_header, (scoreboard_x + 5, scoreboard_y + 3))
        self.screen.blit(name_header, (scoreboard_x + 25, scoreboard_y + 3))
        self.screen.blit(kills_header, (scoreboard_x + 120, scoreboard_y + 3))
        self.screen.blit(score_header, (scoreboard_x + 165, scoreboard_y + 3))
        
        scoreboard_y += 22
        
        # Ligne de séparation
        pygame.draw.line(self.screen, (60, 60, 100), 
                        (scoreboard_x, scoreboard_y - 2), 
                        (scoreboard_x + scoreboard_width - 10, scoreboard_y - 2), 1)
        
        # Joueurs
        for i, (name, score, kills, is_local) in enumerate(all_players[:6]):
            # Fond alterné pour les lignes
            if i % 2 == 0:
                pygame.draw.rect(self.screen, (20, 20, 40), 
                               (scoreboard_x, scoreboard_y, scoreboard_width - 10, row_height - 4))
            
            # Couleur selon le rang
            if i == 0:
                color = YELLOW  # 1er = or
                rank_icon = "🥇"
            elif i == 1:
                color = (192, 192, 192)  # 2e = argent
                rank_icon = "🥈"
            elif i == 2:
                color = (205, 127, 50)  # 3e = bronze
                rank_icon = "🥉"
            else:
                color = WHITE
                rank_icon = f"{i+1}"
            
            # Surligne le joueur local
            if is_local:
                pygame.draw.rect(self.screen, (0, 100, 150, 100), 
                               (scoreboard_x, scoreboard_y, scoreboard_width - 10, row_height - 4), 2)
                color = CYAN
            
            # Rang
            rank_text = self.small_font.render(rank_icon, True, color)
            self.screen.blit(rank_text, (scoreboard_x + 3, scoreboard_y + 4))
            
            # Nom (tronqué si trop long)
            display_name = name[:10] + ".." if len(name) > 10 else name
            name_text = self.small_font.render(display_name, True, color)
            self.screen.blit(name_text, (scoreboard_x + 25, scoreboard_y + 4))
            
            # Kills
            kills_text = self.small_font.render(str(kills), True, color)
            self.screen.blit(kills_text, (scoreboard_x + 130, scoreboard_y + 4))
            
            # Score
            score_text = self.small_font.render(str(score), True, color)
            self.screen.blit(score_text, (scoreboard_x + 165, scoreboard_y + 4))
            
            scoreboard_y += row_height
            
            # Ligne de séparation entre les joueurs
            pygame.draw.line(self.screen, (40, 40, 80), 
                           (scoreboard_x + 5, scoreboard_y - 4), 
                           (scoreboard_x + scoreboard_width - 15, scoreboard_y - 4), 1)
        
        # ═══════════════════════════════════════════════════
        # ÉCRAN DE MORT / RESPAWN
        # ═══════════════════════════════════════════════════
        
        if self.is_dead:
            # Assombrir l'écran
            dark_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, 150))
            self.screen.blit(dark_overlay, (0, 0))
            
            # Message de mort
            death_font = pygame.font.Font(None, 72)
            death_text = death_font.render("💀 ÉLIMINÉ!", True, RED)
            death_rect = death_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
            self.screen.blit(death_text, death_rect)
            
            # Compte à rebours
            respawn_seconds = max(0, self.respawn_timer // 60) + 1
            respawn_text = self.font.render(f"Respawn dans {respawn_seconds}s...", True, WHITE)
            respawn_rect = respawn_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
            self.screen.blit(respawn_text, respawn_rect)
        
        # ═══════════════════════════════════════════════════
        # ÉCRAN DE FIN DE PARTIE
        # ═══════════════════════════════════════════════════
        
        if self.game_over:
            # Assombrir l'écran
            dark_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, 200))
            self.screen.blit(dark_overlay, (0, 0))
            
            # Message de fin
            end_font = pygame.font.Font(None, 72)
            end_text = end_font.render("🏆 PARTIE TERMINÉE!", True, YELLOW)
            end_rect = end_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(end_text, end_rect)
            
            # Classement final
            final_y = SCREEN_HEIGHT // 2
            for i, (name, score, kills, is_local) in enumerate(all_players[:4]):
                medal = ["🥇", "🥈", "🥉", ""][i] if i < 3 else ""
                color = YELLOW if i == 0 else WHITE
                final_text = self.font.render(f"{medal} {i+1}. {name}: {score} pts", True, color)
                final_rect = final_text.get_rect(center=(SCREEN_WIDTH // 2, final_y))
                self.screen.blit(final_text, final_rect)
                final_y += 35
        
        # Coordonnées (coin inférieur gauche)
        coords = self.small_font.render(
            f"X: {int(self.local_ship.x)} Y: {int(self.local_ship.y)}", 
            True, GRAY
        )
        self.screen.blit(coords, (10, SCREEN_HEIGHT - 25))
    
    def game_loop(self):
        """Boucle principale du jeu"""
        last_shoot = 0
        shoot_cooldown = 200  # ms
        
        position_update_rate = 50  # ms
        last_position_update = pygame.time.get_ticks()
        
        print("\n🎮 CONTRÔLES:")
        print("   ZQSD/WASD - Bouger")
        print("   Souris - Viser")
        print("   ESPACE ou Clic - Tirer")
        print("   E - Armer la Super Balle 💥")
        print("   SHIFT - Utiliser le boost ⚡")
        print("   V - Activer/Désactiver Micro 🎤")
        print("   ÉCHAP - Quitter")
        print()
        
        while self.running:
            current_time = pygame.time.get_ticks()
            
            # Événements
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        if not self.is_dead and current_time - last_shoot > shoot_cooldown:
                            self.shoot()
                            last_shoot = current_time
                    elif event.key == pygame.K_e:
                        # Armer la super balle
                        if self.super_bullet_available and not self.super_bullet_used:
                            self.super_bullet_armed = not self.super_bullet_armed
                            if self.super_bullet_armed:
                                print("💥 SUPER BALLE ARMÉE! Tirez pour l'utiliser!")
                            else:
                                print("💥 Super balle désarmée")
                    elif event.key == pygame.K_v:
                        self.voice_chat.toggle_mic()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Clic gauche
                        if not self.is_dead and current_time - last_shoot > shoot_cooldown:
                            self.shoot()
                            last_shoot = current_time
            
            # Mise à jour
            self.handle_input()
            self.update_lasers()
            
            # Met à jour la protection au spawn
            if self.spawn_protection:
                self.spawn_protection_timer -= 1
                self.spawn_protection_flash += 1
                if self.spawn_protection_timer <= 0:
                    self.spawn_protection = False
                    print("⚔️  Protection terminée - Vous êtes vulnérable!")
            
            # Met à jour le timer de respawn
            if self.is_dead and self.respawn_timer > 0:
                self.respawn_timer -= 1
            
            # Met à jour la caméra et l'arène
            self.update_camera()
            self.arena.update()
            
            # Envoie position périodiquement
            if current_time - last_position_update > position_update_rate:
                self.send_position()
                last_position_update = current_time
            
            # Dessin
            self.draw()
            
            self.clock.tick(FPS)
        
        self.stop()
    
    def stop(self):
        """Arrête le client"""
        print("🛑 Arrêt du client...")
        self.running = False
        
        # Arrête le voice chat
        self.voice_chat.stop()
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        pygame.quit()
        print("✅ Déconnecté")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <server_ip>")
        print("Exemple: python client.py 192.168.1.100")
        print()
        print("Pour jouer en local: python client.py 127.0.0.1")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    port = 3500
    
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    client = SpaceBattleClient(server_ip, port)
    client.start()

