# nas — passage AMT en Admin Control Mode (MEBx physique)

État constaté le 2026-08-13 : l'AMT de **nas** est **activé mais en Client Control Mode (CCM)**.
En CCM, le consentement KVM est `read-only = ALL` (verrouillé par le firmware) — un code
PIN s'affiche sur l'écran physique à chaque session KVM. nas est **headless** → personne
ne lit le PIN → **KVM inutilisable**. Le SOL (console série) et l'IDER, eux, ne demandent
pas de consentement et fonctionnent en CCM.

Le passage CCM → ACM (qui supprime le consentement) **exige une présence physique** — Intel
l'impose par design (empêche une prise ACM 100 % distante). Deux façons de fournir cette
présence, sans acheter de certificat :

- **MeshCentral `setup.bin` USB (recommandé)** — MeshCentral génère une clé USB qui **injecte
  sa propre racine** dans le ME au boot puis active l'ACM automatiquement. Pas de cert Intel à
  acheter, pas de navigation MEBx à la main. Détail plus bas.
- **MEBx manuel** — taper la conf ACM à la main dans le menu MEBx. Fastidieux, décrit en annexe.

Le *certificat de provisioning AMT* payant (OID `2.16.840.1.113741.1.2.3`, Sectigo/DigiCert)
ne sert QUE pour l'ACM *zéro-touch entièrement à distance* — inutile ici. Le provisioning
host-based (rpc à distance) ne rend, lui, QUE du CCM.

## Voie recommandée : setup.bin USB (aucun cert acheté)

**Piège de départ** : nas est **déjà provisionné en CCM**. Lancer l'USB ACM tel quel échoue avec
`Intel AMT is already provisioned` (MeshCentral issue #2014). Il faut d'abord **désactiver**.

1. **(distant) Désactiver l'AMT de nas → bare-metal.** `meshcmd AmtDeactivate` ou
   `rpc_linux_x64 deactivate -password <AMT-PASS-voir-Vaultwarden>` (CCM se désactive à distance). ⚠️ ceci
   coupe le CCM actuel (SOL/power déjà câblés dans MeshCentral tombent) jusqu'à l'ACM.
2. **(MeshCentral) Groupe ACM + setup.bin.** Device group avec Intel AMT = *Admin Control Mode*,
   puis générer la clé USB (Bare-Metal USB key) — elle embarque la racine du serveur MeshCentral.
3. **(physique, une seule fois) Booter nas sur la clé USB.** Le ME charge la racine et s'active
   en ACM. Confirmer le prompt au boot. ⚠️ = **reboot de nas** (hyperviseur, invités down) →
   fenêtre de maintenance.
4. Si besoin, cliquer **"Activate Network Access"** dans les réglages AMT (issue #2014).
5. **(distant) `User Consent = None`** via WSMAN/MeshCentral → KVM débloqué.

Refs : MeshCentral issues #2014 / #4359 / #4693, discussion #4518 ; blog meshcentral2
« Intel AMT security and activation improvements » (2021-03).

## Annexe : MEBx manuel (si pas d'USB)

## Faits utiles (déjà vérifiés)

- Firmware ME : `16.1.30.2255`, SKU AMT Pro Corporate.
- Mot de passe AMT du parc **`<AMT-PASS-voir-Vaultwarden>` fonctionne** sur nas (rpc local validé).
- IP actuelle du ME : `10.0.80.188` (DHCP, VLAN 80), MAC ME `00:f0:b4:0f:8d:07`
  (distincte de la MAC OS). **Aucun port AMT ouvert** en CCM host-based
  (16992/16993/16994/16995/623 fermés) — le listener réseau est éteint, d'où l'intérêt du MEBx.
- Port SOL AMT de nas = **ttyS4** (PCI `00:16.3`, `[8086:7aeb]` Alder Lake KT Redirection).
  `serial-getty@ttyS4` est **déjà activé** (login shell dès que la redirection sera joignable).
- Outil `/root/rpc_linux_x64` copié sur nas (depuis ms01) pour diagnostic local.

## Procédure MEBx (déplacement physique requis)

1. Brancher un écran + clavier sur nas, redémarrer.
2. Au POST, `Ctrl-P` pour entrer dans le **MEBx**. Mot de passe par défaut `admin`
   (le firmware force un changement au premier accès — utiliser `<AMT-PASS-voir-Vaultwarden>`).
3. **Intel(R) AMT Configuration** :
   - `User Consent` → `Consent Type` = **None** (supprime le PIN KVM). *Impossible en CCM,
     accessible seulement une fois en ACM/MEBx.*
   - `Manageability Feature Selection` = ON, `SOL/IDER/KVM` = tous **Enabled**.
   - `Network Setup` → `TCP/IP Settings` : idéalement **IP statique dédiée ME sur le VLAN 10
     de management** (cohérent avec ms01 en `10.0.10.13`) — p.ex. `10.0.10.14/24`,
     gw `10.0.10.1`, dns `10.0.10.50`. À exclure du pool DHCP MikroTik.
   - `Activate Network Access` (bascule en ACM avec cette conf).
4. Sortir, sauvegarder. Vérifier depuis nas : `/root/rpc_linux_x64 amtinfo` doit montrer
   `Control Mode: activated in admin control mode`.

## Après l'ACM (à distance)

- Réactiver les features au cas où : `rpc_linux_x64 configure amtfeatures -password <AMT-PASS-voir-Vaultwarden> -kvm -sol -ider`.
- Vérifier ports : `16993`+`16995` OPEN (TLS) — cf. réglage TLS d'ms01, [[ms01-vpro-amt]].
- Ajouter nas dans MeshCentral comme **device AMT** (groupe `NETSYNK - vPro`), host = IP du ME,
  user `admin`, TLS. Correctif `legacy.cnf` déjà en place côté serveur, cf. [[meshcentral-ct650]].

## Attente réaliste

Même en ACM, le KVM de nas affichera la **console texte** (GRUB, boot, `tty1` login),
**pas un bureau graphique** : nas ne fait tourner aucun serveur X (c'est un hyperviseur).
Pour un Proxmox, cette console hors-bande EST le bon outil.
