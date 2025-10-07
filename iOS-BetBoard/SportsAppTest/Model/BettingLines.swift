//
//  BettingLines.swift
//  Updated to support multiple sportsbooks
//

import Foundation

// Keep the original BettingLines for compatibility
struct BettingLines: Identifiable, Codable {
    let id: String
    let gameID: String
    let moneyline: [String: Double]
    let spread: [String: Double]
    let total: [String: Double]
}

// New structure to hold all sportsbook data
struct MultipleSportsbookLines: Identifiable, Codable {
    let id: String
    let gameID: String
    let allSportsbooks: [String: SportsbookLines]
    
    // Get lines for a specific sportsbook
    func lines(for sportsbook: Sportsbook) -> SportsbookLines? {
        let key = sportsbook.rawValue.lowercased()
        return allSportsbooks[key]
    }
    
    // Get available sportsbooks
    var availableSportsbooks: [Sportsbook] {
        return allSportsbooks.keys.compactMap { key in
            switch key {
            case "draftkings": return .draftkings
            case "fanduel": return .fanduel
            case "betmgm": return .betmgm
            case "caesars": return .caesars
            case "pointsbet": return .pointsbet
            case "barstool": return .barstool
            default: return nil
            }
        }.sorted { $0.displayName < $1.displayName }
    }
    
    // Convert to old BettingLines format for a specific sportsbook
    func toBettingLines(for sportsbook: Sportsbook) -> BettingLines {
        let lines = self.lines(for: sportsbook) ?? SportsbookLines.empty()
        return BettingLines(
            id: id,
            gameID: gameID,
            moneyline: lines.moneyline,
            spread: lines.spread,
            total: lines.total
        )
    }
}

struct SportsbookLines: Codable {
    let moneyline: [String: Double]
    let spread: [String: Double]
    let total: [String: Double]
    
    static func empty() -> SportsbookLines {
        return SportsbookLines(moneyline: [:], spread: [:], total: [:])
    }
}
