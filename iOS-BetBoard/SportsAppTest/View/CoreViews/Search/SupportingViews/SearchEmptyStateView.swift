//
//  SearchEmptyStateView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.

import SwiftUI

struct SearchEmptyStateView: View {
    let onPopularSearchTap: (String) -> Void
    @State private var bounceOffset: CGFloat = 0
    
    // Popular teams by conference
    let topTeams = ["Duke", "UNC", "Kansas", "Gonzaga", "Kentucky", "Villanova"]
    let powerConferences = ["ACC", "Big Ten", "SEC", "Big 12", "Big East"]
    
    var body: some View {
        ScrollView {
            VStack(spacing: 32) {
                // Animated basketball on court
                ZStack {
                    // Court
                    RoundedRectangle(cornerRadius: 8)
                        .fill(
                            LinearGradient(
                                colors: [Color.brown.opacity(0.3), Color.brown.opacity(0.1)],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .frame(width: 200, height: 120)
                        .overlay(
                            // Court lines
                            VStack {
                                Circle()
                                    .stroke(Color.white.opacity(0.5), lineWidth: 2)
                                    .frame(width: 60, height: 60)
                            }
                        )
                    
                    // Bouncing basketball
                    Image(systemName: "basketball.fill")
                        .font(.system(size: 50))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [Color.orange, Color.red],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .offset(y: bounceOffset)
                        .onAppear {
                            withAnimation(
                                Animation.easeInOut(duration: 0.6)
                                    .repeatForever(autoreverses: true)
                            ) {
                                bounceOffset = -20
                            }
                        }
                }
                
                // Main message
                VStack(spacing: 12) {
                    Text("The Court is Empty!")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.primary)
                    
                    Text("Search for your favorite teams to find games")
                        .font(.body)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                
                // Popular teams section
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        Image(systemName: "star.fill")
                            .font(.caption)
                            .foregroundColor(.yellow)
                        
                        Text("Popular Teams")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.primary)
                    }
                    
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                        GridItem(.flexible())
                    ], spacing: 12) {
                        ForEach(topTeams, id: \.self) { team in
                            Button(action: {
                                onPopularSearchTap(team)
                            }) {
                                HStack {
                                    Image(systemName: "magnifyingglass")
                                        .font(.caption2)
                                    Text(team)
                                        .font(.subheadline)
                                        .fontWeight(.medium)
                                }
                                .foregroundColor(.blue)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 10)
                                .background(Color.blue.opacity(0.1))
                                .cornerRadius(8)
                            }
                        }
                    }
                }
                .padding()
                .background(Color(.systemBackground))
                .cornerRadius(16)
                .shadow(color: .black.opacity(0.05), radius: 4)
                
                // Power conferences section
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        Image(systemName: "shield.fill")
                            .font(.caption)
                            .foregroundColor(.blue)
                        
                        Text("Power Conferences")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.primary)
                    }
                    
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible())
                    ], spacing: 12) {
                        ForEach(powerConferences, id: \.self) { conference in
                            Button(action: {
                                onPopularSearchTap(conference)
                            }) {
                                HStack {
                                    Image(systemName: "magnifyingglass")
                                        .font(.caption2)
                                    Text(conference)
                                        .font(.subheadline)
                                        .fontWeight(.medium)
                                }
                                .foregroundColor(.purple)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 10)
                                .background(Color.purple.opacity(0.1))
                                .cornerRadius(8)
                            }
                        }
                    }
                }
                .padding()
                .background(Color(.systemBackground))
                .cornerRadius(16)
                .shadow(color: .black.opacity(0.05), radius: 4)
                
                // Pro tip
                HStack(spacing: 8) {
                    Image(systemName: "lightbulb.fill")
                        .foregroundColor(.yellow)
                    
                    Text("Pro tip: Try searching by team abbreviations like 'UNC' or 'UK'")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(8)
            }
            .padding()
        }
    }
}

#Preview {
    SearchEmptyStateView { team in
        print("Selected: \(team)")
    }
}
