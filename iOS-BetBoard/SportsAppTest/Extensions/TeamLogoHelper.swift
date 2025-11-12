//
//  TeamLogoHelper.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/30/25.
//

import SwiftUI

struct TeamLogoHelper {
    /// Converts a team short name to the corresponding logo filename
    /// Example: "Michigan State" -> "michigan_state"
    static func logoFilename(for teamShortName: String) -> String {
        // Normalize the team name: convert to lowercase and trim whitespace
        let normalized = teamShortName.lowercased().trimmingCharacters(in: .whitespaces)
        
        // Simply replace spaces with underscores to create the filename
        return normalized.replacingOccurrences(of: " ", with: "_")
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
