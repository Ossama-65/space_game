#!/usr/bin/env python3
"""
Test minimal de pygame pour voir si ça marche
"""

import sys

print("🔍 Test de pygame...")

try:
    import pygame
    print("✅ Pygame importé avec succès!")
    
    pygame.init()
    print("✅ Pygame initialisé!")
    
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("Test Pygame")
    print("✅ Fenêtre créée!")
    
    print("\n🎉 TOUT FONCTIONNE!")
    print("   Une fenêtre devrait être visible")
    print("   Fermez-la pour continuer")
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        screen.fill((0, 100, 0))  # Vert
        
        # Dessine du texte
        font = pygame.font.Font(None, 36)
        text = font.render("Pygame OK!", True, (255, 255, 255))
        screen.blit(text, (100, 130))
        
        pygame.display.flip()
    
    pygame.quit()
    print("✅ Test terminé avec succès!")
    
except ImportError as e:
    print(f"❌ Pygame n'est pas installé!")
    print(f"   Erreur: {e}")
    print(f"\n💡 Solution: pip3 install --user pygame")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

