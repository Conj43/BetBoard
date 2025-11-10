//
//  BetSlipUI.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct BetSlipUI: View {
    let betSlip: BetSlip
    var onTrackBet: ((BetType, String, Double, Double) -> Void)?
    
    @State private var selectedBetType: BetType = .spread // Default to spread instead of moneyline
    @State private var selectedBet: (String, Double)?
    @State private var betAmount: String = ""
    @State private var selectedSportsbook: Sportsbook = .draftkings
    
    // Available sportsbooks for this game
    private var availableSportsbooks: [Sportsbook] {
        if let allBettingLines = betSlip.allBettingLines {
            var sportsbooks: [Sportsbook] = []
            if allBettingLines.draftkings != nil { sportsbooks.append(.draftkings) }
            if allBettingLines.betmgm != nil { sportsbooks.append(.betmgm) }
            if allBettingLines.fanduel != nil { sportsbooks.append(.fanduel) }
            if allBettingLines.caesars != nil { sportsbooks.append(.caesars) }
            if allBettingLines.pointsbet != nil { sportsbooks.append(.pointsbet) }
            if allBettingLines.barstool != nil { sportsbooks.append(.barstool) }
            return sportsbooks
        }
        return [.draftkings]
    }
    
    // Get betting lines for selected sportsbook
    private var currentBettingLines: BettingLines {
        if let allBettingLines = betSlip.allBettingLines {
            switch selectedSportsbook {
            case .draftkings:
                return allBettingLines.draftkings ?? betSlip.bettingLines
            case .betmgm:
                return allBettingLines.betmgm ?? betSlip.bettingLines
            case .fanduel:
                return allBettingLines.fanduel ?? betSlip.bettingLines
            case .caesars:
                return allBettingLines.caesars ?? betSlip.bettingLines
            case .pointsbet:
                return allBettingLines.pointsbet ?? betSlip.bettingLines
            case .barstool:
                return allBettingLines.barstool ?? betSlip.bettingLines
            }
        }
        return betSlip.bettingLines
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // Header with matchup and game info
            BetSlipHeaderView(betSlip: betSlip)
            
            // Sportsbook selector
            SportsbookSelectorView(
                availableSportsbooks: availableSportsbooks,
                selectedSportsbook: $selectedSportsbook
            )
            
            // Bet type selector and options
            BetTypeAndOptionsView(
                selectedBetType: $selectedBetType,
                currentBettingLines: currentBettingLines,
                selectedBet: $selectedBet,
                onBetAmountChange: { betAmount = "" }
            )
            
            // Prediction info (if available)
            if let predictionInfo = betSlip.predictionInfo {
                PredictionSectionView(prediction: predictionInfo)
            }
            
            // Track Bet Button with Amount Input
            if let selectedBet = selectedBet {
                TrackBetSectionView(
                    selection: selectedBet.0,
                    odds: selectedBet.1,
                    selectedBetType: selectedBetType,
                    selectedSportsbook: selectedSportsbook,
                    betAmount: $betAmount,
                    onTrackBet: onTrackBet
                )
            }
        }
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .onAppear {
            if let firstSportsbook = availableSportsbooks.first {
                selectedSportsbook = firstSportsbook
            }
        }
        .onChange(of: selectedSportsbook) { _ in
            selectedBet = nil
            betAmount = ""
        }
    }
}
