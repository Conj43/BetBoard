//
//  Game.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated for new Firebase structure

import Foundation

struct Game: Identifiable {
    let id: String
    let homeTeam: String
    let awayTeam: String
    let date: Date
    let status: GameStatus
    let neutralSite: Bool
    let homeConference: String?
    let awayConference: String?
    let torvikHomeRank: Int?
    let torvikAwayRank: Int?
    let tipoffTime: String?
    let season: String?
    let predictedWinner: String?
    let predictionInfo: PredictionInfo?
    
    // Computed property for game ID with date format
    var gameIDWithDate: String {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        let dateStr = dateFormatter.string(from: date)
        return "\(dateStr)_\(id)"
    }

    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd/yyyy - h:mm a"
        return formatter.string(from: date)
    }

    var scoreText: String {
        switch status {
        case .notPlayed: return "NP"
        case .inProgress: return "IP"
        case .final(let home, let away): return "\(home) - \(away)"
        }
    }
}

struct GameResult {
    let homeScore: Int
    let awayScore: Int
    let homeTeam: String
    let awayTeam: String
    
    var winner: String {
        homeScore > awayScore ? "home" : "away"
    }
    
    var finalScore: String {
        "\(awayScore) - \(homeScore)"
    }
    
    var totalPoints: Int {
        homeScore + awayScore
    }
    
    func didBetWin(betType: BetType, selection: String, line: Double? = nil) -> Bool? {
        switch betType {
        case .moneyline:
            // Check if selected team won
            if selection.contains(homeTeam) || selection.uppercased().contains(homeTeam.uppercased()) {
                return homeScore > awayScore
            } else {
                return awayScore > homeScore
            }
            
        case .spread:
            // Parse the spread from selection (e.g., "Alabama St -7.5")
            guard let line = line else { return nil }
            
            if selection.contains(homeTeam) || selection.uppercased().contains(homeTeam.uppercased()) {
                // Home team + spread vs away score
                return Double(homeScore) + line > Double(awayScore)
            } else {
                // Away team + spread vs home score
                return Double(awayScore) + line > Double(homeScore)
            }
            
        case .total:
            guard let line = line else { return nil }
            let total = Double(totalPoints)
            
            if selection.uppercased().contains("OVER") {
                return total > line
            } else {
                return total < line
            }
        }
    }
}
