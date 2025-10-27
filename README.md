# hamta_data_playwright

Repository för skript som med hjälp av Playwright-biblioteket i Python hämtar dataset som kräver klickande innan de kan laddas ned.

## Förutsättningar

För att använda dessa skript krävs:

- **Python** installerat på systemet
- **Playwright-biblioteket** för Python
- **R keyring-paketet** (i vissa skript) för säker autentisiering när användarnamn och lösenord behövs

## Installation

### Python och Playwright

1. Installera Python (om det inte redan är installerat)
2. Installera Playwright-biblioteket:
```bash
pip install playwright
playwright install
```

### R keyring-paketet

För skript som kräver autentisiering, installera keyring-paketet i R:
```r
install.packages("keyring")
```

## Struktur

Skripten är strukturerade så att all kod finns i ett R-skript, som kör igång ett Python-skript med samma namn.

**Exempel:**
- `mitt_skript.R` - R-skriptet som användaren kör
- `mitt_skript.py` - Python-skriptet som anropas av R-skriptet

## Användning

1. Kör R-skriptet för att starta datahämtningen:
```r
source("mitt_skript.R")
```

2. R-skriptet kommer automatiskt att:
   - Anropa motsvarande Python-skript
   - Hantera eventuell autentisiering via keyring (om det krävs)
   - Hämta och ladda ned datasetet

## Säkerhet

För skript som kräver autentisiering används R:s keyring-paket för att säkert lagra och hämta användarnamn och lösenord. Detta innebär att känsliga uppgifter inte lagras i klartext i skripten.

## Licens

Detta projekt är licensierat under GNU General Public License v3.0 - se [LICENSE](LICENSE) filen för detaljer.