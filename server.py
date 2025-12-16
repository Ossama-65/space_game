#!/usr/bin/env python3
"""
🚀 SPACE BATTLE - SERVEUR
Jeu de combat spatial multijoueur (jusqu'à 4 joueurs)
5 manches de 2 minutes chacune
Port: 3500
"""

import socket
import threading
import json
import time
import random
from typing import Dict, List

# Constantes de la map
MAP_WIDTH = 2000
MAP_HEIGHT = 1500

class Player:
    def __init__(self, player_id: int, connection: socket.socket, address, name: str = None):
        self.id = player_id
        self.connection = connection
        self.address = address
        self.name = name or f"Joueur{player_id}"
        self.x = MAP_WIDTH // 2
        self.y = MAP_HEIGHT // 2
        self.angle = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.health = 100
        self.color = self.get_color(player_id)
        self.active = True
        self.spawn_protected = True
        self.spawn_protection_time = time.time()
        
        # Stats de la partie
        self.score = 0
        self.kills = 0
        self.deaths = 0
        
        # État du joueur
        self.is_dead = False
        self.respawn_time = 0
        
    def get_color(self, player_id):
        colors = ["blue", "red", "green", "yellow"]
        return colors[(player_id - 1) % len(colors)]
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "angle": self.angle,
            "vx": self.vx,
            "vy": self.vy,
            "health": self.health,
            "color": self.color,
            "spawn_protected": self.spawn_protected,
            "score": self.score,
            "kills": self.kills,
            "deaths": self.deaths,
            "is_dead": self.is_dead
        }
    
    def update_spawn_protection(self):
        """Met à jour la protection au spawn (3 secondes)"""
        if self.spawn_protected:
            if time.time() - self.spawn_protection_time > 3.0:
                self.spawn_protected = False
    
    def respawn(self):
        """Fait réapparaître le joueur"""
        self.is_dead = False
        self.health = 100
        # Position aléatoire sur la map
        self.x = random.randint(200, MAP_WIDTH - 200)
        self.y = random.randint(200, MAP_HEIGHT - 200)
        self.vx = 0
        self.vy = 0
        # Protection au respawn
        self.spawn_protected = True
        self.spawn_protection_time = time.time()
        print(f"🔄 {self.name} a réapparu!")
    
    def die(self):
        """Le joueur meurt"""
        self.is_dead = True
        self.deaths += 1
        self.respawn_time = time.time() + 3.0  # Respawn dans 3 secondes


class HealthPickup:
    """Pickup de soin (seringue)"""
    def __init__(self, pickup_id, x, y):
        self.id = pickup_id
        self.x = x
        self.y = y
        self.heal_amount = 50
        self.active = True
    
    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "type": "health",
            "active": self.active
        }


class SpaceBattleServer:
    def __init__(self, port=3500, max_players=4):
        self.port = port
        self.max_players = max_players
        self.players: Dict[int, Player] = {}
        self.next_player_id = 1
        self.running = False
        self.server_socket = None
        
        # Système de manches
        self.total_rounds = 5
        self.current_round = 0
        self.round_duration = 120  # 2 minutes en secondes
        self.round_start_time = 0
        self.round_active = False
        self.game_started = False
        self.game_over = False
        
        # Super balle (toutes les 15 secondes)
        self.super_bullet_active = False
        self.last_super_bullet_time = 0
        self.super_bullet_interval = 15  # secondes
        
        # Pickups de santé
        self.health_pickups: Dict[int, HealthPickup] = {}
        self.next_pickup_id = 1
        self.last_pickup_spawn = 0
        self.pickup_spawn_interval = 30  # secondes
        
    def start(self):
        """Démarre le serveur"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(self.max_players)
            self.running = True
            
            print(f"╔══════════════════════════════════════════════════╗")
            print(f"║  🚀 SERVEUR SPACE BATTLE - MODE COMPÉTITIF     ║")
            print(f"╚══════════════════════════════════════════════════╝")
            print(f"")
            print(f"📡 Port: {self.port}")
            print(f"👥 Joueurs max: {self.max_players}")
            print(f"🏆 Manches: {self.total_rounds} (2 min chacune)")
            print(f"💉 Pickup santé: +50 HP toutes les 30s")
            print(f"💥 Super balle: toutes les 15s")
            print(f"🌐 En attente de connexions...")
            print(f"")
            print(f"💡 Les joueurs doivent se connecter avec:")
            print(f"   python client.py <votre_ip>")
            print(f"")
            
            # Thread pour accepter les connexions
            accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
            accept_thread.start()
            
            # Boucle principale du jeu
            self.game_loop()
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    def accept_connections(self):
        """Accepte les nouvelles connexions"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                
                if len(self.players) >= self.max_players:
                    client_socket.send(json.dumps({"error": "Serveur plein"}).encode())
                    client_socket.close()
                    continue
                
                player_id = self.next_player_id
                self.next_player_id += 1
                
                # Envoie l'ID au joueur d'abord
                colors = ["blue", "red", "green", "yellow"]
                color = colors[(player_id - 1) % 4]
                welcome_msg = {
                    "type": "welcome",
                    "player_id": player_id,
                    "color": color
                }
                client_socket.send((json.dumps(welcome_msg) + '\n').encode())
                
                # Attend le nom du joueur
                player_name = f"Joueur{player_id}"
                try:
                    client_socket.settimeout(10)
                    data = client_socket.recv(4096)
                    client_socket.settimeout(None)
                    
                    if data:
                        lines = data.decode().strip().split('\n')
                        for line in lines:
                            if line.strip():
                                name_msg = json.loads(line)
                                if name_msg.get("type") == "set_name":
                                    player_name = name_msg.get("name", player_name)[:20]
                                    break
                except:
                    pass
                
                # Crée le joueur avec le nom
                player = Player(player_id, client_socket, address, player_name)
                self.players[player_id] = player
                
                print(f"✅ Joueur {player_id} ({player_name}) connecté: {address}")
                
                # Démarre la partie si c'est le premier joueur
                if not self.game_started and len(self.players) >= 1:
                    self.start_game()
                
                # Thread pour gérer ce joueur
                player_thread = threading.Thread(
                    target=self.handle_player, 
                    args=(player,), 
                    daemon=True
                )
                player_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"⚠️  Erreur connexion: {e}")
    
    def start_game(self):
        """Démarre la partie"""
        self.game_started = True
        self.game_over = False
        self.current_round = 0
        
        # Reset les scores
        for player in self.players.values():
            player.score = 0
            player.kills = 0
            player.deaths = 0
        
        self.start_new_round()
    
    def start_new_round(self):
        """Démarre une nouvelle manche"""
        self.current_round += 1
        self.round_start_time = time.time()
        self.round_active = True
        self.last_super_bullet_time = time.time()
        self.last_pickup_spawn = time.time()
        self.super_bullet_active = False
        
        # Clear les pickups
        self.health_pickups.clear()
        
        # Reset tous les joueurs
        for player in self.players.values():
            player.health = 100
            player.is_dead = False
            player.x = random.randint(200, MAP_WIDTH - 200)
            player.y = random.randint(200, MAP_HEIGHT - 200)
            player.spawn_protected = True
            player.spawn_protection_time = time.time()
        
        print(f"\n🏁 MANCHE {self.current_round}/{self.total_rounds} DÉMARRÉE!")
        print(f"   Durée: 2 minutes")
        
        # Annonce la nouvelle manche
        self.broadcast({
            "type": "round_start",
            "round": self.current_round,
            "total_rounds": self.total_rounds
        })
    
    def end_round(self):
        """Termine la manche en cours"""
        self.round_active = False
        
        # Calcule les scores de la manche
        print(f"\n🏁 MANCHE {self.current_round} TERMINÉE!")
        print("   Scores:")
        
        sorted_players = sorted(self.players.values(), key=lambda p: p.kills, reverse=True)
        for i, player in enumerate(sorted_players):
            # Points bonus pour le classement
            bonus = [100, 50, 25, 10][i] if i < 4 else 0
            player.score += bonus + (player.kills * 10)
            print(f"   {i+1}. {player.name}: {player.kills} kills, {player.deaths} morts (+{bonus} bonus)")
        
        # Annonce la fin de manche
        self.broadcast({
            "type": "round_end",
            "round": self.current_round,
            "scores": {p.id: {"score": p.score, "kills": p.kills, "deaths": p.deaths} 
                      for p in self.players.values()}
        })
        
        if self.current_round >= self.total_rounds:
            self.end_game()
        else:
            # Pause de 5 secondes entre les manches
            time.sleep(5)
            # Reset kills/deaths pour la prochaine manche
            for player in self.players.values():
                player.kills = 0
                player.deaths = 0
            self.start_new_round()
    
    def end_game(self):
        """Termine la partie"""
        self.game_over = True
        self.round_active = False
        
        # Trouve le gagnant
        sorted_players = sorted(self.players.values(), key=lambda p: p.score, reverse=True)
        
        print(f"\n🏆 PARTIE TERMINÉE!")
        print("   Classement final:")
        for i, player in enumerate(sorted_players):
            medal = ["🥇", "🥈", "🥉", ""][i] if i < 4 else ""
            print(f"   {medal} {i+1}. {player.name}: {player.score} points")
        
        # Annonce la fin de partie
        self.broadcast({
            "type": "game_over",
            "winner": sorted_players[0].name if sorted_players else "Personne",
            "final_scores": {p.id: {"name": p.name, "score": p.score} 
                           for p in self.players.values()}
        })
    
    def spawn_health_pickup(self):
        """Fait apparaître un pickup de santé"""
        pickup_id = self.next_pickup_id
        self.next_pickup_id += 1
        
        x = random.randint(200, MAP_WIDTH - 200)
        y = random.randint(200, MAP_HEIGHT - 200)
        
        pickup = HealthPickup(pickup_id, x, y)
        self.health_pickups[pickup_id] = pickup
        
        print(f"💉 Pickup de santé apparu en ({x}, {y})")
        
        # Annonce le pickup
        self.broadcast({
            "type": "pickup_spawn",
            "pickup": pickup.to_dict()
        })
    
    def handle_player(self, player: Player):
        """Gère les messages d'un joueur"""
        buffer = ""
        try:
            while self.running and player.active:
                data = player.connection.recv(4096)
                if not data:
                    break
                
                buffer += data.decode()
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            self.process_message(player, message)
                        except json.JSONDecodeError as e:
                            pass
                    
        except Exception as e:
            print(f"⚠️  Erreur joueur {player.id}: {e}")
        finally:
            self.disconnect_player(player.id)
    
    def process_message(self, player: Player, message: dict):
        """Traite un message d'un joueur"""
        msg_type = message.get("type")
        
        # Ignore les messages si le joueur est mort
        if player.is_dead and msg_type in ["move", "shoot"]:
            return
        
        if msg_type == "set_name":
            player.name = message.get("name", player.name)[:20]
            print(f"📝 Joueur {player.id} renommé en: {player.name}")
            
        elif msg_type == "move":
            player.x = message.get("x", player.x)
            player.y = message.get("y", player.y)
            player.angle = message.get("angle", player.angle)
            player.vx = message.get("vx", player.vx)
            player.vy = message.get("vy", player.vy)
            
        elif msg_type == "shoot":
            is_super = message.get("is_super", False)
            
            shoot_msg = {
                "type": "player_shoot",
                "player_id": player.id,
                "x": message.get("x"),
                "y": message.get("y"),
                "angle": message.get("angle"),
                "is_super": is_super
            }
            self.broadcast(shoot_msg, exclude_player=player.id)
            
        elif msg_type == "hit":
            target_id = message.get("target_id")
            is_super = message.get("is_super", False)
            damage = 40 if is_super else 20  # Super balle = 40 dégâts, normale = 20
            
            if target_id in self.players:
                target = self.players[target_id]
                
                # Ignore si le joueur est protégé ou mort
                if target.spawn_protected or target.is_dead:
                    return
                
                target.health -= damage
                
                if target.health <= 0:
                    target.health = 0
                    target.die()
                    player.kills += 1
                    print(f"💀 {target.name} éliminé par {player.name}! {'(SUPER BALLE)' if is_super else ''}")
        
        elif msg_type == "pickup_collect":
            pickup_id = message.get("pickup_id")
            if pickup_id in self.health_pickups:
                pickup = self.health_pickups[pickup_id]
                if pickup.active:
                    pickup.active = False
                    player.health = min(100, player.health + pickup.heal_amount)
                    print(f"💉 {player.name} a ramassé un soin (+{pickup.heal_amount} HP)")
                    del self.health_pickups[pickup_id]
                    
                    # Annonce la collecte
                    self.broadcast({
                        "type": "pickup_collected",
                        "pickup_id": pickup_id,
                        "player_id": player.id
                    })
        
        elif msg_type == "voice":
            voice_msg = {
                "type": "voice",
                "player_id": player.id,
                "audio": message.get("audio")
            }
            self.broadcast(voice_msg, exclude_player=player.id)
    
    def game_loop(self):
        """Boucle principale du jeu"""
        last_update = time.time()
        update_rate = 1/20
        
        try:
            while self.running:
                current_time = time.time()
                
                # Met à jour tous les joueurs
                for player in self.players.values():
                    player.update_spawn_protection()
                    
                    # Gère le respawn
                    if player.is_dead and current_time >= player.respawn_time:
                        player.respawn()
                
                # Gestion de la manche
                if self.round_active:
                    elapsed = current_time - self.round_start_time
                    
                    # Vérifie si la manche est terminée
                    if elapsed >= self.round_duration:
                        self.end_round()
                    else:
                        # Super balle toutes les 15 secondes
                        if current_time - self.last_super_bullet_time >= self.super_bullet_interval:
                            self.super_bullet_active = True
                            self.last_super_bullet_time = current_time
                            print("💥 SUPER BALLE DISPONIBLE!")
                            self.broadcast({"type": "super_bullet_available"})
                        
                        # Pickup de santé toutes les 30 secondes
                        if current_time - self.last_pickup_spawn >= self.pickup_spawn_interval:
                            self.spawn_health_pickup()
                            self.last_pickup_spawn = current_time
                
                # Envoie l'état du jeu
                if current_time - last_update >= update_rate:
                    self.send_game_state()
                    last_update = current_time
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\n🛑 Arrêt du serveur...")
    
    def send_game_state(self):
        """Envoie l'état du jeu à tous les joueurs"""
        if not self.players:
            return
        
        # Calcule le temps restant
        time_remaining = 0
        if self.round_active:
            elapsed = time.time() - self.round_start_time
            time_remaining = max(0, self.round_duration - elapsed)
        
        game_state = {
            "type": "game_state",
            "players": [p.to_dict() for p in self.players.values() if p.active],
            "round": self.current_round,
            "total_rounds": self.total_rounds,
            "time_remaining": time_remaining,
            "round_active": self.round_active,
            "game_over": self.game_over,
            "super_bullet_available": self.super_bullet_active,
            "health_pickups": [p.to_dict() for p in self.health_pickups.values() if p.active]
        }
        
        self.broadcast(game_state)
    
    def broadcast(self, message: dict, exclude_player=None):
        """Envoie un message à tous les joueurs"""
        data = (json.dumps(message) + '\n').encode()
        
        for player_id, player in list(self.players.items()):
            if player_id == exclude_player:
                continue
                
            try:
                player.connection.send(data)
            except:
                player.active = False
    
    def disconnect_player(self, player_id: int):
        """Déconnecte un joueur"""
        if player_id in self.players:
            player = self.players[player_id]
            player.active = False
            
            try:
                player.connection.close()
            except:
                pass
            
            del self.players[player_id]
            print(f"❌ Joueur {player_id} déconnecté")
            
            if self.running:
                self.broadcast({
                    "type": "player_left",
                    "player_id": player_id
                })
    
    def stop(self):
        """Arrête le serveur"""
        self.running = False
        
        for player in list(self.players.values()):
            try:
                player.connection.close()
            except:
                pass
        
        if self.server_socket:
            self.server_socket.close()
        
        print("✅ Serveur arrêté")


if __name__ == "__main__":
    import sys
    
    port = 3500
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    server = SpaceBattleServer(port=port)
    server.start()
