# 🚀 Space Battle - Version Python (SANS Unity!)

## ✨ Jeu Prêt à Lancer - Aucune Installation Complexe!

Un jeu de combat spatial multijoueur **qui tourne directement sur votre PC**!
- Port **3500** (comme demandé)
- Jusqu'à **4 joueurs**
- **Pas besoin d'Unity!** Juste Python et Pygame

---

## ⚡ LANCEMENT ULTRA-RAPIDE (3 Minutes)

### 1️⃣ Installer Python (si pas déjà fait)

**Mac** (vous êtes sur Mac):
```bash
# Python est déjà installé! Vérifiez:
python3 --version

# Si pas de Python ou version < 3.7:
brew install python3
```

**Windows**:
- Téléchargez sur [python.org](https://python.org)
- Cochez "Add Python to PATH" pendant l'installation

**Linux**:
```bash
sudo apt install python3 python3-pip
```

---

### 2️⃣ Installer Pygame (1 commande!)

```bash
# Mac/Linux:
pip3 install pygame

# Windows:
pip install pygame
```

✅ **C'est tout! Installation terminée!**

---

### 3️⃣ LANCER LE JEU!

#### 🎮 Mode Solo (Test sur votre PC)

**Terminal 1 - Serveur**:
```bash
cd /Users/ossama/Downloads/test_Zineb/SpaceGame_Python
python3 server.py
```

Vous verrez:
```
╔══════════════════════════════════════════════╗
║  🚀 SERVEUR SPACE BATTLE DÉMARRÉ!          ║
╚══════════════════════════════════════════════╝

📡 Port: 3500
👥 Joueurs max: 4
🌐 En attente de connexions...
```

**Terminal 2 - Client** (nouvelle fenêtre):
```bash
cd /Users/ossama/Downloads/test_Zineb/SpaceGame_Python
python3 client.py 127.0.0.1
```

🎮 **Une fenêtre de jeu s'ouvre! Vous jouez!**

---

#### 🌐 Mode Multijoueur (2-4 PCs)

**Sur le PC Serveur (le vôtre)**:

1. **Trouvez votre IP**:
   ```bash
   ifconfig | grep "inet "
   # Cherchez quelque chose comme: 192.168.1.100
   ```

2. **Lancez le serveur**:
   ```bash
   python3 server.py
   ```

3. **Dites votre IP à vos amis**: Ex: `192.168.1.100`

**Sur les PCs Clients (vos amis)**:

1. **Ils téléchargent juste `client.py`** (ou le dossier entier)

2. **Ils lancent**:
   ```bash
   python3 client.py 192.168.1.100
   ```
   (Remplacez par votre vraie IP)

3. **Ils apparaissent dans le jeu!** 🎉

---

## 🎮 CONTRÔLES

```
┌────────────────────────────────────┐
│  ZQSD / WASD  →  Bouger            │
│  SOURIS       →  Viser             │
│  ESPACE       →  Tirer 💥         │
│  CLIC GAUCHE  →  Tirer (alternatif)│
│  ÉCHAP        →  Quitter           │
└────────────────────────────────────┘
```

**Astuce**: Visez avec la souris, bougez avec ZQSD!

---

## 🌟 Fonctionnalités

✅ **Multijoueur 2-4 joueurs** sur port 3500  
✅ **Combat spatial** avec lasers  
✅ **Système de santé** avec barre de vie  
✅ **4 couleurs** de vaisseaux (bleu, rouge, vert, jaune)  
✅ **Physique spatiale** réaliste  
✅ **Interface simple** et efficace  
✅ **Pas de lag** (optimisé!)  

---

## 🔧 Résolution de Problèmes

### "pygame not found"
```bash
pip3 install pygame
```

### "Connection refused"
→ Le serveur n'est pas lancé. Lancez `server.py` d'abord!

### "Port already in use"
→ Le port 3500 est occupé. Lancez avec un autre port:
```bash
python3 server.py 3501
python3 client.py 127.0.0.1 3501
```

### Firewall bloque le port 3500
**Mac**:
```bash
# Ajoutez Python aux exceptions du firewall
Système > Sécurité > Pare-feu > Options > +
```

**Windows**:
```powershell
New-NetFirewallRule -DisplayName "SpaceBattle" -Direction Inbound -Protocol TCP -LocalPort 3500 -Action Allow
```

---

## 📊 Architecture

**Serveur (`server.py`)**:
- Écoute sur le port **3500**
- Accepte jusqu'à **4 joueurs**
- Synchronise les positions à **20 Hz**
- Gère les collisions et la santé

**Client (`client.py`)**:
- Se connecte au serveur
- Affiche le jeu avec **Pygame**
- Envoie les inputs au serveur
- Reçoit les mises à jour

**Communication**: TCP Socket + JSON

---

## 🎯 Comparaison: Python vs Unity

| Critère | Python (Ce jeu) | Unity |
|---------|-----------------|-------|
| **Installation** | 1 commande | 2-3 heures |
| **Lancement** | Immédiat | Setup complexe |
| **Taille** | ~10 KB | ~2 GB |
| **Graphismes** | 2D Simple | 3D Avancé |
| **Performance** | ✅ Léger | Gourmand |
| **Facilité** | ⭐⭐⭐⭐⭐ | ⭐⭐ |

**Cette version = Parfaite pour jouer MAINTENANT!**

---

## 🚀 Améliorations Futures (Facile à ajouter)

- [ ] Effets sonores (pew pew!)
- [ ] Explosions animées
- [ ] Power-ups (vie, speed, armes)
- [ ] Score et classement
- [ ] Astéroïdes
- [ ] Plus d'armes
- [ ] Fond spatial animé
- [ ] Minimap

---

## 📝 Notes Techniques

**Langage**: Python 3.7+  
**Bibliothèque**: Pygame 2.x  
**Protocole**: TCP  
**Port**: 3500 (configurable)  
**FPS**: 60  
**Tick Rate**: 20 Hz  

**Code**: ~800 lignes de Python pur!

---

## 🎉 C'EST PRÊT!

Vous avez maintenant un **vrai jeu multijoueur** qui tourne sur le **port 3500** de votre PC!

**Pas d'Unity. Pas de complexité. Juste du fun!** 🚀✨

---

## 📞 Questions?

**"Ça marche vraiment?"**  
→ Oui! Testez en solo d'abord (127.0.0.1)

**"Mes amis peuvent rejoindre?"**  
→ Oui! Donnez-leur votre IP et ils lancent client.py

**"C'est gratuit?"**  
→ Totalement! Python et Pygame sont libres

**"C'est mieux qu'Unity?"**  
→ Plus simple et plus rapide à lancer! Unity a de meilleurs graphismes 3D

---

**Amusez-vous bien! 🎮**

*Jeu créé spécialement pour lancer sur port 3500 sans Unity!*

