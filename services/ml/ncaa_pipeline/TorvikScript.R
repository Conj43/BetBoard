library(cbbdata)
library(dplyr)
library(readr)

out_csv <- "~/Desktop/School Work/2025 Fall/Capstone II/TestBetBoard/torvik_daily.csv"

# Ensure logged in
try(cbd_logout(), silent = TRUE)
cbd_login()

# Grab the full archive in one call
res <- cbd_torvik_ratings_archive()

stopifnot(!is.null(res), nrow(res) > 0)

# Convert to data.frame (so we can subset normally)
res <- as.data.frame(res)

# Keep common fields
wanted <- c("team","conf","rank","barthag","adj_o","adj_d","adj_t","luck","date","as_of_date")
keep   <- intersect(wanted, names(res))
res    <- res[, keep, drop = FALSE]

# Standardize date column
if (!"as_of_date" %in% names(res) && "date" %in% names(res)) {
  res <- dplyr::rename(res, as_of_date = date)
}

dir.create(dirname(out_csv), recursive = TRUE, showWarnings = FALSE)
write_csv(res, out_csv)

cat("Wrote:", out_csv,
    "rows:", nrow(res),
    "days:", length(unique(res$as_of_date)), "\n")