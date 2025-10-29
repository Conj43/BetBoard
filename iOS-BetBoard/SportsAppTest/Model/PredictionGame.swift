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
    
    // Add explicit initializer to ensure all properties are set correctly
    init(
        homeTeam: Team,
        awayTeam: Team,
        gameTime: Date,
        bestBet: BestBet,
        confidence: Double,
        analysis: String?,
        keyFactors: [String],
        betSlip: BetSlip
    ) {
        self.homeTeam = homeTeam
        self.awayTeam = awayTeam
        self.gameTime = gameTime
        self.bestBet = bestBet
        self.confidence = confidence
        self.analysis = analysis
        self.keyFactors = keyFactors
        self.betSlip = betSlip
    }
}

struct BestBet {
    let type: BetType
    let selection: String
    let odds: Double
    let sportsbook: Sportsbook
    
    // Add explicit initializer
    init(type: BetType, selection: String, odds: Double, sportsbook: Sportsbook) {
        self.type = type
        self.selection = selection
        self.odds = odds
        self.sportsbook = sportsbook
    }
}
