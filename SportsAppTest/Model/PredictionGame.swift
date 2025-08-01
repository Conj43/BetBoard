//
//  PredictionGame.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import Foundation

struct PredictionGame: Identifiable {
    let id = UUID()
    let homeTeam: Team
    let awayTeam: Team
    let gameTime: Date
    let bestBet: BestBet
    let confidence: Double
    let analysis: String?
    let keyFactors: [String]
    let betSlip: BetSlip
    
    var formattedGameTime: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd - h:mm a"
        return formatter.string(from: gameTime)
    }
}

struct BestBet {
    let type: BetType
    let selection: String
    let odds: Double
    let sportsbook: Sportsbook
}
