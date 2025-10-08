//
//  TrackedBetsSectionView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI

struct TrackedBetsSectionView: View {
    let trackedBets: [BetWithGameInfo]
    let onBetTap: (BetWithGameInfo) -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Tracked Bets")
                    .font(.headline)
                    .fontWeight(.semibold)
                Spacer()
                NavigationLink("See All", destination: AllTrackedBetsView())
                    .font(.subheadline)
                    .foregroundColor(.blue)
            }
            
            if trackedBets.isEmpty {
                TrackedBetsEmptyStateView {
                    // This closure is called when user taps "Browse Games"
                    // You'll need to handle navigation to the Search tab
                    // For now, we can leave it empty or print a message
                    print("Navigate to Search tab")
                }
            } else {
                ForEach(trackedBets.prefix(3)) { bet in
                    TrackedBetRowView(bet: bet) {
                        onBetTap(bet)
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
}

struct HistoricalBetsSectionView: View {
    let recentBets: [BetWithGameInfo]
    let onBetTap: (BetWithGameInfo) -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Recent Bets")
                    .font(.headline)
                    .fontWeight(.semibold)
                Spacer()
                NavigationLink("See All", destination: BetHistoryView())
                    .font(.subheadline)
                    .foregroundColor(.blue)
            }
            
            if recentBets.isEmpty {
                Text("No recent bets")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding()
            } else {
                ForEach(recentBets.prefix(5)) { bet in
                    HistoricalBetRowView(bet: bet) {
                        onBetTap(bet)
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
}

// Placeholder for All Tracked Bets View
struct AllTrackedBetsView: View {
    var body: some View {
        VStack {
            Text("All Tracked Bets")
            Text("(Feature coming soon)")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .navigationTitle("Tracked Bets")
        .navigationBarTitleDisplayMode(.inline)
    }
}
