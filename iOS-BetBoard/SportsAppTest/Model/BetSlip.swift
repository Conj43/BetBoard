//
//  BetSlip.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated to remove moneyline features

import Foundation

struct BetSlip: Identifiable, Codable {
    let id: String
    let gameID: String
    let sportsbook: Sportsbook
    let homeTeam: Team
    let awayTeam: Team
    let gameTime: Date
    let tipoffTimeString: String? 
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
    // Removed moneyline prediction fields
    // Keeping with default values for backward compatibility
    let moneylineConfidence: Double = 0.0 // Fixed to 0.0
    let moneylineBet: String? = nil       // Fixed to nil
    
    // Spread prediction
    let spreadConfidence: Double // 0.0 to 100.0
    let spreadBet: String?
    
    // Total prediction
    let totalConfidence: Double // 0.0 to 100.0
    let totalBet: String?
    
    // Optional analysis
    let analysis: String?
    
    // Custom initializer for creating without moneyline
    init(spreadConfidence: Double, spreadBet: String?, totalConfidence: Double, totalBet: String?, analysis: String?) {
        self.spreadConfidence = spreadConfidence
        self.spreadBet = spreadBet
        self.totalConfidence = totalConfidence
        self.totalBet = totalBet
        self.analysis = analysis
    }
    
    // For backward compatibility: create from new Firebase structure
    static func fromFirebaseData(spreadData: [String: Any]?, totalData: [String: Any]?, analysis: String?) -> PredictionInfo? {
        // Extract spread data
        let spreadConfidence: Double
        let spreadBet: String?
        
        if let spread = spreadData {
            if let edge = spread["edge"] as? Double, let line = spread["predicted_margin"] as? Double, let pick = spread["pick"] as? String {
                // Calculate confidence based on edge (could adjust this algorithm)
                spreadConfidence = min(abs(edge) * 10, 100) // Simple scaling
                // Format spread bet string
                spreadBet = formatSpreadBet(pick: pick, line: line)
            } else {
                spreadConfidence = 0
                spreadBet = nil
            }
        } else {
            spreadConfidence = 0
            spreadBet = nil
        }
        
        // Extract total data
        let totalConfidence: Double
        let totalBet: String?
        
        if let total = totalData {
            if let edge = total["edge"] as? Double, let line = total["predicted_total"] as? Double, let pick = total["pick"] as? String {
                // Calculate confidence based on edge
                totalConfidence = min(abs(edge) * 10, 100) // Simple scaling
                // Format total bet string
                totalBet = formatTotalBet(pick: pick, line: line)
            } else {
                totalConfidence = 0
                totalBet = nil
            }
        } else {
            totalConfidence = 0
            totalBet = nil
        }
        
        // Only create prediction info if we have valid data
        if spreadConfidence > 0 || totalConfidence > 0 {
            return PredictionInfo(
                spreadConfidence: spreadConfidence,
                spreadBet: spreadBet,
                totalConfidence: totalConfidence,
                totalBet: totalBet,
                analysis: analysis
            )
        }
        
        return nil
    }
    
    // Helper to format spread bet string
    private static func formatSpreadBet(pick: String, line: Double) -> String {
        return "\(pick) \(line > 0 ? "+" : "")\(String(format: "%.1f", line))"
    }
    
    // Helper to format total bet string
    private static func formatTotalBet(pick: String, line: Double) -> String {
        return "\(pick) \(String(format: "%.1f", line))"
    }
    
    // Computed property to get the highest confidence bet (for backward compatibility)
    var recommendedBet: String? {
        // Find the bet with highest confidence (only spread and total now)
        let confidences: [(bet: String?, confidence: Double)] = [
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
        return max(spreadConfidence, totalConfidence)
    }
    
    // CodingKeys to handle the absence of moneyline fields in serialization
    enum CodingKeys: String, CodingKey {
        case spreadConfidence, spreadBet, totalConfidence, totalBet, analysis
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
