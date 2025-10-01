//
//  BetSlipDetailView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI
import FirebaseAuth

struct BetSlipDetailView: View {
    let betSlip: BetSlip
    @State private var showingTrackConfirmation = false
    @State private var trackedBetDetails: String = ""
    @State private var isTrackingBet = false
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                BetSlipUI(betSlip: betSlip) { betType, selection, odds, amount in
                    trackSelectedBet(betType: betType, selection: selection, odds: odds, amount: amount)
                }
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle("Game Details")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Bet Tracked!", isPresented: $showingTrackConfirmation) {
            Button("OK") { }
        } message: {
            Text("Successfully tracked: \(trackedBetDetails)")
        }
        .disabled(isTrackingBet)
    }
    
    private func trackSelectedBet(betType: BetType, selection: String, odds: Double, amount: Double) {
        trackedBetDetails = "\(selection) for $\(String(format: "%.2f", amount)) at \(formatOdds(odds))"
        isTrackingBet = true
        
        Task {
            await trackBetToFirebase(betType: betType, selection: selection, odds: odds, amount: amount)
        }
    }
    
    private func trackBetToFirebase(betType: BetType, selection: String, odds: Double, amount: Double) async {
        guard let currentUser = Auth.auth().currentUser else {
            await MainActor.run {
                isTrackingBet = false
            }
            return
        }
        
        let firebaseService = FirebaseService()
        let bet = Bet(
            id: UUID().uuidString,
            userID: currentUser.uid,
            gameID: betSlip.gameID,
            type: betType,
            selection: selection,
            odds: odds,
            amount: amount,
            result: .pending,
            placedAt: Date()
        )
        
        do {
            try await firebaseService.addUserBet(bet)
            await MainActor.run {
                isTrackingBet = false
                showingTrackConfirmation = true
            }
        } catch {
            // Handle error appropriately
            print("Failed to track bet: \(error)")
            await MainActor.run {
                isTrackingBet = false
                // You could show an error alert here
            }
        }
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
}

#Preview {
    // Create a sample BetSlip for preview with correct initializers
    let sampleBetSlip = BetSlip(
        id: "preview-betslip",
        gameID: "sample-game",
        sportsbook: .draftkings,
        homeTeam: Team(
            id: "home-team",
            name: "Duke Blue Devils",
            shortName: "DUKE",
            logoURL: "",
            record: TeamRecord(wins: 23, losses: 8),
            conference: "ACC",
            ranking: 9,
            colorHex: "#001A57"
        ),
        awayTeam: Team(
            id: "away-team",
            name: "North Carolina Tar Heels",
            shortName: "UNC",
            logoURL: "",
            record: TeamRecord(wins: 21, losses: 10),
            conference: "ACC",
            ranking: 15,
            colorHex: "#4B9CD3"
        ),
        gameTime: Date(),
        bettingLines: BettingLines(
            id: "preview-lines",
            gameID: "sample-game",
            moneyline: ["DUKE": -150, "UNC": 130],
            spread: ["DUKE -3.5": -110, "UNC +3.5": -110],
            total: ["Over 145.5": -110, "Under 145.5": -110]
        ),
        allBettingLines: nil, // No multiple sportsbooks for this preview
        predictionInfo: PredictionInfo(
            confidence: 85.0,
            recommendedBet: "UNC +3.5",
            analysis: "Strong defensive matchup favors the underdog"
        ),
        neutralSite: false
    )
    
    NavigationView {
        BetSlipDetailView(betSlip: sampleBetSlip)
    }
}
