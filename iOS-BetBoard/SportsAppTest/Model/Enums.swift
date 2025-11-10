//
//  Enums.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated to mark moneyline as deprecated

import Foundation

enum BetType: String, Codable {
    case moneyline // Kept for backward compatibility with existing bets
    case spread
    case total
    
    // Check if bet type is supported in current version
    var isSupported: Bool {
        switch self {
        case .moneyline:
            return false // Moneyline is no longer supported
        case .spread, .total:
            return true
        }
    }
    
    // Display name for UI
    var displayName: String {
        switch self {
        case .moneyline:
            return "Moneyline (Deprecated)"
        case .spread:
            return "Spread"
        case .total:
            return "Total"
        }
    }
    
    // Available bet types for new bets
    static var supportedTypes: [BetType] {
        return [.spread, .total]
    }
}

enum BetResult: String, Codable {
    case won
    case lost
    case push
    case pending
}

enum GameStatus: Codable {
    case notPlayed
    case inProgress
    case final(home: Int, away: Int)

    enum CodingKeys: String, CodingKey {
        case state, homeScore, awayScore
    }

    enum StateValue: String, Codable {
        case NP
        case IP
        case FINAL
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let state = try container.decode(StateValue.self, forKey: .state)

        switch state {
        case .NP:
            self = .notPlayed
        case .IP:
            self = .inProgress
        case .FINAL:
            let home = try container.decode(Int.self, forKey: .homeScore)
            let away = try container.decode(Int.self, forKey: .awayScore)
            self = .final(home: home, away: away)
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        switch self {
        case .notPlayed:
            try container.encode(StateValue.NP, forKey: .state)
        case .inProgress:
            try container.encode(StateValue.IP, forKey: .state)
        case .final(let home, let away):
            try container.encode(StateValue.FINAL, forKey: .state)
            try container.encode(home, forKey: .homeScore)
            try container.encode(away, forKey: .awayScore)
        }
    }
}
