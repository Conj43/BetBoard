//
//  BettingLines.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated to remove moneyline features

import Foundation

// Keep the original BettingLines for compatibility
struct BettingLines: Identifiable, Codable {
    let id: String
    let gameID: String
    let moneyline: [String: Double]
    let spread: [String: Double]
    let total: [String: Double]
    
    // Factory method to create an instance with empty moneyline
    static func create(id: String, gameID: String, moneyline: [String: Double], spread: [String: Double], total: [String: Double]) -> BettingLines {
        return BettingLines(id: id, gameID: gameID, moneyline: moneyline, spread: spread, total: total)
    }
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
        return BettingLines.create(
            id: id,
            gameID: gameID,
            moneyline: lines.moneyline,
            spread: lines.spread,
            total: lines.total
        )
    }
}

struct SportsbookLines: Codable {
    // Keeping moneyline for backward compatibility but it will be empty
    let moneyline: [String: Double]
    let spread: [String: Double]
    let total: [String: Double]
    
    static func empty() -> SportsbookLines {
        return SportsbookLines(moneyline: [:], spread: [:], total: [:])
    }
    
    // Factory method to create without moneyline
    static func create(spread: [String: Double], total: [String: Double]) -> SportsbookLines {
        return SportsbookLines(moneyline: [:], spread: spread, total: total)
    }
}
