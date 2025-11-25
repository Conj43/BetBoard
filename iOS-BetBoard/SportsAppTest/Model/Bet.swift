//
//  Bet.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation

struct Bet: Identifiable, Codable {
    let id: String
    let userID: String
    let gameID: String
    let type: BetType
    let selection: String
    let odds: Double
    let amount: Double
    let result: BetResult
    let placedAt: Date

    // New, all optional so old data still works
    let homeTeamName: String?
    let awayTeamName: String?
    let gameDate: Date?
    let sportsbook: Sportsbook?

    init(
        id: String,
        userID: String,
        gameID: String,
        type: BetType,
        selection: String,
        odds: Double,
        amount: Double,
        result: BetResult,
        placedAt: Date,
        homeTeamName: String? = nil,
        awayTeamName: String? = nil,
        gameDate: Date? = nil,
        sportsbook: Sportsbook? = nil
    ) {
        self.id = id
        self.userID = userID
        self.gameID = gameID
        self.type = type
        self.selection = selection
        self.odds = odds
        self.amount = amount
        self.result = result
        self.placedAt = placedAt
        self.homeTeamName = homeTeamName
        self.awayTeamName = awayTeamName
        self.gameDate = gameDate
        self.sportsbook = sportsbook
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
