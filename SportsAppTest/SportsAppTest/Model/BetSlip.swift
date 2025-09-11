//
//  BetSlip.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//


//
//  BetSlip.swift
//  SportsApp
//
//  Created by Trenton Roney on 7/14/25.
//


import Foundation

struct BetSlip: Identifiable, Codable {
    let id: String
    let gameID: String
    let sportsbook: Sportsbook
    let homeTeam: Team
    let awayTeam: Team
    let gameTime: Date
    let bettingLines: BettingLines
    let predictionInfo: PredictionInfo?
    let neutralSite: Bool
    
    var formattedGameTime: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd - h:mm a"
        return formatter.string(from: gameTime)
    }
}

struct PredictionInfo: Codable {
    let confidence: Double // 0.0 to 1.0
    let recommendedBet: String?
    let analysis: String?
    
    var confidencePercentage: String {
        return "\(Int(confidence))%"
    }
}

enum Sportsbook: String, Codable, CaseIterable {
    case draftkings = "DraftKings"
    case fanduel = "FanDuel"
    case betmgm = "BetMGM"
    case caesars = "Caesars"
    case pointsbet = "PointsBet"
    case barstool = "Barstool"
    
    var displayName: String {
        return self.rawValue
    }
    
    var logoName: String {
        switch self {
        case .draftkings: return "draftkings_logo"
        case .fanduel: return "fanduel_logo"
        case .betmgm: return "betmgm_logo"
        case .caesars: return "caesars_logo"
        case .pointsbet: return "pointsbet_logo"
        case .barstool: return "barstool_logo"
        }
    }
}

// Firebase Implementation
// {
//   "id": "betslip123",
//   "gameID": "game123",
//   "sportsbook": "DraftKings",
//   "homeTeam": { ... },
//   "awayTeam": { ... },
//   "gameTime": "2025-07-14T18:30:00Z",
//   "bettingLines": { ... },
//   "predictionInfo": {
//     "confidence": 0.75,
//     "recommendedBet": "UNC +3.5",
//     "analysis": "Strong defensive matchup favors the underdog"
//   },
//   "neutralSite": true
// }
