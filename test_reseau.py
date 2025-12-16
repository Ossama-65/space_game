#!/usr/bin/env python3
"""
Script de diagnostic réseau pour Space Battle
Aide à comprendre pourquoi la connexion ne marche pas
"""

import socket
import sys

def test_port(host, port):
    """Test si on peut se connecter à un serveur"""
    print(f"\n🔍 Test de connexion à {host}:{port}...")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        print(f"✅ SUCCÈS! Le serveur {host}:{port} est accessible!")
        s.close()
        return True
    except socket.timeout:
        print(f"❌ TIMEOUT: Le serveur ne répond pas (firewall?)")
        return False
    except ConnectionRefusedError:
        print(f"❌ REFUSÉ: Le serveur n'est pas lancé sur ce port")
        return False
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

def get_local_ip():
    """Obtient l'IP locale"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Impossible de déterminer"

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════╗")
    print("║    🔧 DIAGNOSTIC RÉSEAU - SPACE BATTLE      ║")
    print("╚══════════════════════════════════════════════╝")
    
    # Affiche l'IP locale
    local_ip = get_local_ip()
    print(f"\n📍 Votre IP locale: {local_ip}")
    
    if len(sys.argv) < 2:
        print("\n💡 Usage:")
        print("   Sur le SERVEUR: python test_reseau.py")
        print("   Sur le CLIENT:  python test_reseau.py <IP_serveur>")
        print(f"\n   Exemple: python test_reseau.py {local_ip}")
        sys.exit(0)
    
    server_ip = sys.argv[1]
    port = 3500
    
    print(f"\n🎯 Test depuis ce PC vers {server_ip}:{port}")
    
    # Test de connexion
    if test_port(server_ip, port):
        print("\n✅ Tout est OK! Le jeu devrait fonctionner!")
        print(f"   Lancez: python client.py {server_ip}")
    else:
        print("\n❌ Problème détecté!")
        print("\n🔧 Solutions possibles:")
        print("   1. Vérifiez que le serveur est lancé (python server.py)")
        print("   2. Désactivez le firewall sur le PC serveur")
        print(f"   3. Vérifiez que vous êtes sur le même réseau Wi-Fi")
        print(f"   4. Testez le ping: ping {server_ip}")

