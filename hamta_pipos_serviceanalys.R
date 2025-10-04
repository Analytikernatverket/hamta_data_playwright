
hamta_pipos_serviceanalys <- function(
  returnera_sf = TRUE  
  ) {
  # ==============================================================================================================================
  #
  # En funktion för att hämta olika typer av serviceinrättningar såsom dagligvarubutiker, drivmedelsstationer, apotek etc. från
  # Pipos serviceanalys.
  #
  # Skriptet använder Python och Python-biblioteket Playwright för att automatisera klickandet på webben som krävs för att hämta
  # data från Pipos. Keyring-paketet i R måste vara installerat och ha en service som heter "Pipos" med användarnamn och lösenord
  # för att logga in på Pipos. Läs mer här: https://pipos.se/
  #
  # ==============================================================================================================================
  
  # Ladda nödvändiga paket
  if (!require("pacman")) install.packages("pacman")
  p_load(tidyverse,
         keyring,
         glue,
         readxl)
  if (returnera_sf) p_load(sf)             # ladda sf-paketet om datasetet ska returneras som sf-objekt
  
  # Kontrollera att Python är installerat
  py_path <- Sys.which("python")
  if (py_path == "") stop("❌ Detta skript kräver att Python är installerat. Ingen Python-installation hittades i PATH, åtgärda och kör skriptet igen.")
  
  # Kolla att paketet keyring finns installerat och att service "pipos" finns
  if (!requireNamespace("keyring", quietly = TRUE)) {
    stop("❌ R-paketet 'keyring' är inte installerat, det krävs för att köra denna funktion. Installera keyring och lägg in en service som heter 'pipos' med användare och lösenord till Pipos serviceanalys och prova att köra funktionen igen.",)
  } else if (!"pipos" %in% key_list()$service) {
    stop("❌ Ingen service med namnet 'pipos' hittades i keyring, det krävs för att köra denna funktion. Lägg in en service som heter 'pipos' med användare och lösenord till Pipos serviceanalys och prova att köra funktionen igen.")
  }

  # skapa temporär mapp där datasetet kommer att sparas
  tmpdir <- tempfile()
  dir.create(tmpdir)
  
  pythonskript_sokvag <- "G:/skript/peter/hamta_pipos_serviceanalys.py"
  
  system2("python", c(pythonskript_sokvag, tmpdir))
  sokvag_filnamn <- list.files(tmpdir, full.names = TRUE)
  
  # läs in datasetet från Excelfilen som sparats ned från Pipos serviceanalys
  pipos_sf <- suppressMessages(read_xlsx(sokvag_filnamn)) %>% 
    filter(!if_all(everything(), is.na))
  
  # gör om datasetet till sf-objekt om returnera_sf = TRUE
  if (returnera_sf) {
    pipos_sf <- pipos_sf %>% 
      st_as_sf(coords = c("X", "Y"), crs = 3006)
  }
  
  unlink(tmpdir, recursive = TRUE, force = TRUE)         # radera den temporära filen när vi är klara
  return(pipos_sf)
}
