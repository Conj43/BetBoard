//
//  BetHistoryEmptyStateView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/7/25.
//

import SwiftUI

struct BetHistoryEmptyStateView: View {
    var body: some View {
        ScrollView {
            VStack(spacing: 28) {
                // 3D spinning trophy
                Trophy3DView()
                    .frame(height: 200)
                    .padding(.horizontal, 40)
                    .padding(.top, 10)
                
                // Main message
                VStack(spacing: 12) {
                    Text("Build Your Legacy")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.primary)
                    
                    Text("No betting history yet")
                        .font(.body)
                        .foregroundColor(.secondary)
                    
                    Text("Start tracking bets to see your performance stats")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }
                
                // Future stats preview
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        Image(systemName: "chart.bar.fill")
                            .foregroundColor(.purple)
                        
                        Text("Track Your Success")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                    }
                    
                    // Mock stats cards
                    VStack(spacing: 12) {
                        StatPreviewCard(
                            icon: "percent",
                            title: "Win Rate",
                            description: "See your winning percentage",
                            color: .green
                        )
                        
                        StatPreviewCard(
                            icon: "dollarsign.circle.fill",
                            title: "Total P&L",
                            description: "Track profit and losses",
                            color: .blue
                        )
                        
                        StatPreviewCard(
                            icon: "flame.fill",
                            title: "Streaks",
                            description: "Monitor win/loss streaks",
                            color: .orange
                        )
                        
                        StatPreviewCard(
                            icon: "chart.line.uptrend.xyaxis",
                            title: "ROI",
                            description: "Calculate return on investment",
                            color: .purple
                        )
                    }
                }
                .padding()
                .background(Color(.systemBackground))
                .cornerRadius(16)
                .shadow(color: .black.opacity(0.05), radius: 4)
                
                // Basketball wisdom
                VStack(spacing: 8) {
                    HStack(spacing: 6) {
                        Image(systemName: "quote.opening")
                            .font(.caption2)
                        
                        Text("Basketball Facts")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)
                        
                        Image(systemName: "quote.closing")
                            .font(.caption2)
                    }
                    .foregroundColor(.secondary)
                    
                    Text("Shaun Livingston has never missed a mid-range jumpshot")
                        .font(.caption)
                        .italic()
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }
                .padding()
                .background(
                    LinearGradient(
                        colors: [Color.blue.opacity(0.1), Color.purple.opacity(0.1)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .cornerRadius(12)
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
    }
}

struct StatPreviewCard: View {
    let icon: String
    let title: String
    let description: String
    let color: Color
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(color)
                .frame(width: 40)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.primary)
                
                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            Image(systemName: "lock.fill")
                .font(.caption)
                .foregroundColor(.gray.opacity(0.3))
        }
        .padding()
        .background(Color(.systemGray6).opacity(0.5))
        .cornerRadius(10)
    }
}

#Preview {
    BetHistoryEmptyStateView()
}
