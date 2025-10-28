
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
         httr,
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

  # skapa temporär mapp lokalt där datasetet kommer att sparas tillfälligt
  tmpdir <- tempfile()
  dir.create(tmpdir)

  # hämta Python-skript från Github och spara i en tillfällig mapp för att kunna anropa från system2()
  py_url <- "https://raw.githubusercontent.com/Analytikernatverket/hamta_data_playwright/refs/heads/main/hamta_pipos_serviceanalys.py"
  py_temp <- tempfile(fileext = ".py")
  py_resp <- GET(py_url, add_headers(`Cache-Control` = "no-cache"))
  stop_for_status(py_resp)
  writeBin(httr::content(py_resp, "raw"), py_temp)

  r_sokvag_rscript_exe <- file.path(R.home("bin"), "Rscript.exe")

  system2("python", c(py_temp, tmpdir, r_sokvag_rscript_exe))
  sokvag_filnamn <- list.files(tmpdir, full.names = TRUE)

  # läs in datasetet från Excelfilen som sparats ned från Pipos serviceanalys
  pipos_sf <- suppressMessages(read_xlsx(sokvag_filnamn)) %>%
    filter(!if_all(everything(), is.na))

  # gör om datasetet till sf-objekt om returnera_sf = TRUE
  if (returnera_sf) {
    # ta ut rader som saknar geografi och lägg i egen dataframe
    dataset_utan_geo <- pipos_sf %>%
      filter(is.na(X)) %>%
      select(-c(X, Y))

    # ta bort de som saknar geografi, gör om till sf, och lägg till rader som saknar geografi därefter
    pipos_sf <- pipos_sf %>%
      filter(!is.na(X)) %>%
      st_as_sf(coords = c("X", "Y"), crs = 3006) %>%
      bind_rows(dataset_utan_geo)
  }

  unlink(tmpdir, recursive = TRUE, force = TRUE)         # radera den temporära filen när vi är klara
  return(pipos_sf)
}
