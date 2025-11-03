//
//  TeamNameFormatterExtensions.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 11/3/25.
//

import SwiftUI

// MARK: - Extensions for String to format team names
extension String {
    /// Converts a team name from Firebase format to a properly formatted display name
    var formattedTeamName: String {
        return TeamNameFormatter.formatTeamName(self)
    }
}

// MARK: - Extensions for PredictionBadgeView
extension PredictionBadgeView {
    /// Creates a new PredictionBadgeView with properly formatted team names in the selection
    static func withFormattedTeamName(title: String, selection: String, confidence: Double, iconName: String) -> PredictionBadgeView {
        // Extract team name from selection for formatting
        let formattedSelection: String
        
        if title == "Moneyline" {
            // For moneyline, the selection is just the team name
            formattedSelection = TeamNameFormatter.formatTeamName(selection)
        } else if title == "Spread" {
            // For spread, extract team name and preserve the spread value
            // Format: "TEAMNAME -7.5" or "TEAMNAME +7.5"
            let components = selection.components(separatedBy: " ")
            if components.count >= 2 {
                let teamName = components[0]
                let spreadValue = components[1...].joined(separator: " ")
                formattedSelection = "\(TeamNameFormatter.formatTeamName(teamName)) \(spreadValue)"
            } else {
                formattedSelection = selection
            }
        } else {
            // For other bet types like totals, keep as is
            formattedSelection = selection
        }
        
        return PredictionBadgeView(title: title, selection: formattedSelection, confidence: confidence, iconName: iconName)
    }
}

// MARK: - Extensions for BestBet
extension BestBet {
    /// Returns a formatted display string for the bet selection
    var formattedSelection: String {
        switch type {
        case .moneyline:
            return TeamNameFormatter.formatTeamName(selection)
        case .spread:
            // For spread, format just the team name part
            let components = selection.components(separatedBy: " ")
            if components.count >= 2 {
                let teamName = components[0]
                let spreadValue = components[1...].joined(separator: " ")
                return "\(TeamNameFormatter.formatTeamName(teamName)) \(spreadValue)"
            }
            return selection
        case .total:
            return selection
        }
    }
}

// MARK: - Extensions for Team
extension Team {
    /// Returns a formatted team name for display instead of using shortName directly
    var displayName: String {
        // First try to format using the shortName (which is often in uppercase)
        let formatted = TeamNameFormatter.formatTeamName(shortName)
        
        // If the formatter didn't change anything, try the full name
        if formatted == shortName {
            return name
        }
        return formatted
    }
}
