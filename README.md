# Intel vPro / AMT — Home Assistant integration

Centralisation vPro (Intel AMT) **native dans Home Assistant** : chaque machine devient
un device HA avec contrôle d'alimentation, état et infos — UI/UX = HA (propre, mobile,
dashboards, automations). Remplace MeshCommander (UI années 2000) pour le 90 % d'usage
(power/état). KVM/SOL restent dans MeshCommander de base (fallback conservé).

## Entities (par machine)
- `switch.<machine>_power` — On = power up (AMT 2), Off = soft off (AMT 8)
- `button.<machine>_reset` — master bus reset (10)
- `button.<machine>_power_cycle` — power cycle (5)
- `button.<machine>_boot_to_bios` — next boot → BIOS setup puis reset *(expérimental)*
- `sensor.<machine>_power_state` — on / off / sleep / hibernate
- `sensor.<machine>_amt_version` — version firmware AMT
- `binary_sensor.<machine>_amt_online` — firmware AMT joignable (indépendant de l'OS)

## Prérequis AMT
- AMT provisionné, compte admin (Digest), port **16993** (TLS) ou 16992 (plain)
- HA doit pouvoir joindre l'hôte AMT sur ce port

## Installation
1. Copier `custom_components/vpro/` dans `<config>/custom_components/` de HA
   (ou via HACS : dépôt custom).
2. Redémarrer HA.
3. **Paramètres → Appareils et services → Ajouter → Intel vPro / AMT**.
4. Saisir hôte (ex `192.0.2.61`), `admin`, mot de passe, port 16993, TLS.

## Valider le protocole AMT avant HA (recommandé)
Le client AMT (`amt.py`) est partagé. Tester en standalone contre la vraie machine :
```bash
pip install requests urllib3
python3 tools/amt_test.py 192.0.2.61 admin '<password>' --port 16993
# action (avec confirmation) :
python3 tools/amt_test.py 192.0.2.61 admin '<password>' --action reset
```
Un run vert = la couche protocole de l'intégration est bonne.

## Notes
- TLS AMT = cert auto-signé → vérif désactivée côté client (réseau de gestion).
- AMT peut être en TLS-only (16993) ou plain (16992) selon provisioning.
- `boot_to_bios` fait read-modify-write de `AMT_BootSettingData` puis reset — à valider
  par machine (variations firmware).

## État — validé live (2026-06-28)
Testé contre le vrai AMT de MS-01.

- **Endpoint réel = `192.0.2.20:16992` (plain), admin / Digest.** L'AMT partage l'IP de
  l'hôte et intercepte 16992-16995 ; le `192.0.2.61` de MeshCommander était une entrée
  stale. TLS 16993 = SSLError (stack TLS AMT trop vieille pour openssl moderne) → utiliser
  **plain 16992** (réseau de gestion). Defaults du config_flow = 16992 / TLS off.
- **Lecture validée** : `get_power_state` = 2 (on), `get_versions` = AMT **16.1.25**
  (+ Flash/Netstack/Sku/Build). Les sensors/binary_sensor marchent.
- **Power control bloqué côté AMT** : `RequestPowerStateChange` → SOAP fault
  **`e:AccessDenied`** ("sender was not authorized"). Selectors vérifiés corrects
  (identiques aux clés énumérées) → **le compte `admin` n'a pas le realm "Remote Control"
  / Power**, ou Remote Control est désactivé dans la conf AMT (ou mode CCM vs ACM).
  **À corriger côté AMT** (MEBx / provisioning : donner le realm Remote Control à admin,
  ou re-provisionner en Admin Control Mode). Le code switch/button marchera dès le realm OK.
- **NAS `192.0.2.10`** : host up mais 16992/16993 **refused** → AMT non activé/provisionné.
  Rien à manager tant que l'AMT n'y est pas activé.

## Cibles homelab
- Home Assistant : `192.0.2.50:8123`
- AMT MS-01 : `192.0.2.20:16992` (plain), user `admin`
- AMT NAS : `192.0.2.10` (à activer)
