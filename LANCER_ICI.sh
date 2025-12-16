#!/bin/bash
# 🚀 Script de lancement automatique du jeu
# Double-cliquez sur ce fichier pour lancer le jeu!

clear

echo "╔══════════════════════════════════════════════╗"
echo "║     🚀 SPACE BATTLE - LANCEUR RAPIDE       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Vérifie Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé!"
    echo "   Installez-le avec: brew install python3"
    exit 1
fi

# Vérifie Pygame
if ! python3 -c "import pygame" 2>/dev/null; then
    echo "📦 Installation de Pygame..."
    pip3 install pygame
fi

echo "✅ Prêt!"
echo ""
echo "Choisissez:"
echo "  1) HÉBERGER (Serveur)"
echo "  2) REJOINDRE (Client)"
echo ""
read -p "Votre choix (1 ou 2): " choice

case $choice in
    1)
        echo ""
        echo "🎮 Lancement du SERVEUR sur port 3500..."
        echo ""
        python3 server.py
        ;;
    2)
        echo ""
        read -p "IP du serveur (ou 127.0.0.1 pour local): " server_ip
        echo ""
        echo "🎮 Connexion à $server_ip:3500..."
        echo ""
        python3 client.py "$server_ip"
        ;;
    *)
        echo "❌ Choix invalide!"
        exit 1
        ;;
esac

