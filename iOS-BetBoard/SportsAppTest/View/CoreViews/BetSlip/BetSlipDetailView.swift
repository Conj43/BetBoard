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
