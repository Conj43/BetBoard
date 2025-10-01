//
//  TeamLogoHelper.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/30/25.
//


//
//  TeamLogoHelper.swift
//  SportsAppTest
//
//  Helper to map team names to logo filenames
//

import SwiftUI

struct TeamLogoHelper {
    /// Converts a team short name to the corresponding logo filename
    /// Example: "UNC" -> "north_carolina"
    static func logoFilename(for teamShortName: String) -> String {
        let normalized = teamShortName.lowercased().trimmingCharacters(in: .whitespaces)
        
        // Map common team short names to their logo filenames
        let teamMapping: [String: String] = [
            // ACC Teams
            "unc": "north_carolina",
            "duke": "duke",
            "uva": "virginia",
            "virginia": "virginia",
            "ncsu": "north_carolina_state",
            "ncstate": "north_carolina_state",
            "wake": "wake_forest",
            "wake forest": "wake_forest",
            "clemson": "clemson",
            "fsu": "florida_state",
            "florida state": "florida_state",
            "louisville": "louisville",
            "miami": "miami_fl",
            "pitt": "pittsburgh",
            "pittsburgh": "pittsburgh",
            "syracuse": "syracuse",
            "vt": "virginia_tech",
            "virginia tech": "virginia_tech",
            "bc": "boston_college",
            "boston college": "boston_college",
            "gt": "georgia_tech",
            "georgia tech": "georgia_tech",
            "notre dame": "notre_dame",
            
            // Big Ten
            "michigan": "michigan",
            "ohio state": "ohio_state",
            "msu": "michigan_state",
            "michigan state": "michigan_state",
            "penn state": "penn_state",
            "indiana": "indiana",
            "purdue": "purdue",
            "illinois": "illinois",
            "iowa": "iowa",
            "wisconsin": "wisconsin",
            "minnesota": "minnesota",
            "northwestern": "northwestern",
            "nebraska": "nebraska",
            "maryland": "maryland",
            "rutgers": "rutgers",
            
            // Big 12
            "kansas": "kansas",
            "ku": "kansas",
            "k-state": "kansas_state",
            "kansas state": "kansas_state",
            "texas": "texas",
            "texas tech": "texas_tech",
            "tcu": "tcu",
            "baylor": "baylor",
            "oklahoma": "oklahoma",
            "oklahoma state": "oklahoma_state",
            "iowa state": "iowa_state",
            "west virginia": "west_virginia",
            
            // SEC
            "kentucky": "kentucky",
            "uk": "kentucky",
            "tennessee": "tennessee",
            "alabama": "alabama",
            "auburn": "auburn",
            "florida": "florida",
            "georgia": "georgia",
            "lsu": "lsu",
            "arkansas": "arkansas",
            "mississippi state": "mississippi_state",
            "ole miss": "mississippi",
            "missouri": "missouri",
            "south carolina": "south_carolina",
            "texas a&m": "texas_am",
            "vanderbilt": "vanderbilt",
            
            // Pac-12
            "arizona": "arizona",
            "ucla": "ucla",
            "usc": "southern_california",
            "oregon": "oregon",
            "washington": "washington",
            "stanford": "stanford",
            "cal": "california",
            "colorado": "colorado",
            "utah": "utah",
            
            // Big East
            "villanova": "villanova",
            "nova": "villanova",
            "georgetown": "georgetown",
            "marquette": "marquette",
            "creighton": "creighton",
            "xavier": "xavier",
            "providence": "providence",
            "st. john's": "st_johns_ny",
            "seton hall": "seton_hall",
            "butler": "butler",
            "depaul": "depaul",
            
            // Other Notable Teams
            "gonzaga": "gonzaga",
            "memphis": "memphis",
            "houston": "houston",
            "uconn": "connecticut",
            "connecticut": "connecticut",
        ]
        
        // Return mapped name or try to use the normalized name directly
        return teamMapping[normalized] ?? normalized.replacingOccurrences(of: " ", with: "_")
    }
    
    /// Loads a UIImage for a given team
    static func loadLogo(for teamShortName: String) -> UIImage? {
        let filename = logoFilename(for: teamShortName)
        
        // Try loading from ncaa_logos folder
        if let image = UIImage(named: "ncaa_logos/\(filename)") {
            return image
        }
        
        // Try without folder path
        if let image = UIImage(named: filename) {
            return image
        }
        
        // Try with .png extension explicitly
        if let image = UIImage(named: "ncaa_logos/\(filename).png") {
            return image
        }
        
        return nil
    }
}

// SwiftUI Image extension for easier usage
extension Image {
    init(teamLogo teamShortName: String) {
        if let uiImage = TeamLogoHelper.loadLogo(for: teamShortName) {
            self.init(uiImage: uiImage)
        } else {
            // Fallback to system image
            self.init(systemName: "sportscourt.fill")
        }
    }
}
