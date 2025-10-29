//
//  BetSlip.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation

struct BetSlip: Identifiable, Codable {
    let id: String
    let gameID: String
    let sportsbook: Sportsbook
    let homeTeam: Team
    let awayTeam: Team
    let gameTime: Date
    let bettingLines: BettingLines // Default/fallback betting lines
    let allBettingLines: AllSportsbookLines? // All sportsbook lines
    let predictionInfo: PredictionInfo?
    let neutralSite: Bool
    
    var formattedGameTime: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd - h:mm a"
        return formatter.string(from: gameTime)
    }
}

// Structure to hold all sportsbook betting lines
struct AllSportsbookLines: Codable {
    let draftkings: BettingLines?
    let betmgm: BettingLines?
    let fanduel: BettingLines?
    let caesars: BettingLines?
    let pointsbet: BettingLines?
    let barstool: BettingLines?
    
    // Custom initializer for direct creation
    init(draftkings: BettingLines? = nil,
         betmgm: BettingLines? = nil,
         fanduel: BettingLines? = nil,
         caesars: BettingLines? = nil,
         pointsbet: BettingLines? = nil,
         barstool: BettingLines? = nil) {
        self.draftkings = draftkings
        self.betmgm = betmgm
        self.fanduel = fanduel
        self.caesars = caesars
        self.pointsbet = pointsbet
        self.barstool = barstool
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        draftkings = try container.decodeIfPresent(BettingLines.self, forKey: .draftkings)
        betmgm = try container.decodeIfPresent(BettingLines.self, forKey: .betmgm)
        fanduel = try container.decodeIfPresent(BettingLines.self, forKey: .fanduel)
        caesars = try container.decodeIfPresent(BettingLines.self, forKey: .caesars)
        pointsbet = try container.decodeIfPresent(BettingLines.self, forKey: .pointsbet)
        barstool = try container.decodeIfPresent(BettingLines.self, forKey: .barstool)
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(draftkings, forKey: .draftkings)
        try container.encodeIfPresent(betmgm, forKey: .betmgm)
        try container.encodeIfPresent(fanduel, forKey: .fanduel)
        try container.encodeIfPresent(caesars, forKey: .caesars)
        try container.encodeIfPresent(pointsbet, forKey: .pointsbet)
        try container.encodeIfPresent(barstool, forKey: .barstool)
    }
    
    enum CodingKeys: String, CodingKey {
        case draftkings, betmgm, fanduel, caesars, pointsbet, barstool
    }
}

struct PredictionInfo: Codable {
    // Moneyline prediction
    let moneylineConfidence: Double // 0.0 to 100.0
    let moneylineBet: String?
    
    // Spread prediction
    let spreadConfidence: Double // 0.0 to 100.0
    let spreadBet: String?
    
    // Total prediction
    let totalConfidence: Double // 0.0 to 100.0
    let totalBet: String?
    
    // Optional analysis
    let analysis: String?
    
    // Computed property to get the highest confidence bet (for backward compatibility)
    var recommendedBet: String? {
        // Find the bet with highest confidence
        let confidences: [(bet: String?, confidence: Double)] = [
            (moneylineBet, moneylineConfidence),
            (spreadBet, spreadConfidence),
            (totalBet, totalConfidence)
        ]
        
        return confidences
            .filter { $0.bet != nil }
            .max(by: { $0.confidence < $1.confidence })?
            .bet
    }
    
    // Computed property to get the highest confidence value (for backward compatibility)
    var confidence: Double {
        return max(moneylineConfidence, max(spreadConfidence, totalConfidence))
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
