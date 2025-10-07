//
//  EnhancedBet.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/27/25.
//

import Foundation

// Enhanced bet structure that includes game info
struct BetWithGameInfo: Identifiable, Hashable {
    let bet: Bet
    let homeTeam: String
    let awayTeam: String
    let gameDate: Date
    
    var id: String { bet.id }
    
    var gameMatchup: String {
        return "\(awayTeam) @ \(homeTeam)"
    }
    
    var formattedGameDate: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd"
        return formatter.string(from: gameDate)
    }
    
    // MARK: - Hashable Conformance
    func hash(into hasher: inout Hasher) {
        hasher.combine(bet.id)
    }
    
    static func == (lhs: BetWithGameInfo, rhs: BetWithGameInfo) -> Bool {
        return lhs.bet.id == rhs.bet.id
    }
}
