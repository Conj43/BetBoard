//
//  Bet.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation

struct Bet: Identifiable, Codable, Hashable {
    let id: String
    let userID: String
    let gameID: String
    let type: BetType
    let selection: String
    let odds: Double
    let amount: Double
    let result: BetResult
    let placedAt: Date
    
    // MARK: - Hashable Conformance
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
    
    static func == (lhs: Bet, rhs: Bet) -> Bool {
        return lhs.id == rhs.id
    }
}

// Firebase Implementation
// {
//   "id": "bet123",
//   "userID": "user456",
//   "gameID": "game123",
//   "type": "spread",
//   "selection": "UNC +3.5",
//   "odds": -110,
//   "amount": 50.0,
//   "result": "pending",
//   "placedAt": "2025-07-10T14:00:00Z"
// }
