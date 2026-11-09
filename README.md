# Outil de dimensionnement ECS & tampon primaire (FWM PRO)

Application Streamlit qui simule un ballon tampon primaire couplé à une station d'eau chaude sanitaire FWM PRO (70, 90 ou 170), seule ou en cascade jusqu'à 6 modules.

Elle calcule :
- le temps de chauffe de la PAC entre la T° de redémarrage et la T° de consigne ;
- le volume d'ECS soutirable et l'autonomie avant redémarrage ;
- l'autonomie totale avec la PAC en marche ;
- la capacité de débit estimée de la cascade, à la consigne et en fin de tranche.

Les capacités des stations sont indicatives : débit mesuré à 60 °C primaire / 45 °C ECS, puis extrapolé linéairement selon l'écart primaire/ECS.

## Lancer l'application

```bash
pip install -r requirements.txt
streamlit run app.py
```
