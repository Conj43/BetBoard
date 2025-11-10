//
//  Game.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated for new Firebase structure

import Foundation

struct Game: Identifiable, Codable {
    let id: String
    let homeTeam: String // Will store home_team value from Firebase
    let awayTeam: String // Will store away_team value from Firebase
    let date: Date
    let status: GameStatus
    let neutralSite: Bool
    let homeConference: String? // New field for home conference
    let awayConference: String? // New field for away conference
    let torvikHomeRank: Int? // New field for Torvik ranking
    let torvikAwayRank: Int? // New field for Torvik ranking
    let tipoffTime: String? // New field for tipoff time
    let season: String? // New field for season
    
    // Model fields that might not be needed:
    // - p_win_home, p_win_away: Not needed as probabilities are removed
    // - predicted_winner: Keeping for reference
    let predictedWinner: String?
    
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
    
    // CodingKeys for decoding Firebase data
    enum CodingKeys: String, CodingKey {
        case id = "game_id"
        case homeTeam = "home_team"
        case awayTeam = "away_team"
        case date
        case status
        case neutralSite = "neutral_site"
        case homeConference = "home_conf"
        case awayConference = "away_conf"
        case torvikHomeRank = "torvik_home_rank"
        case torvikAwayRank = "torvik_away_rank"
        case tipoffTime = "tipoff_time"
        case season
        case predictedWinner = "predicted_winner"
    }
}
