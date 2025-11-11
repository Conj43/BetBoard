//
//  SportsbookSelectorView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 11/11/25.
//

import SwiftUI

struct SportsbookSelectorView: View {
    let availableSportsbooks: [Sportsbook]
    @Binding var selectedSportsbook: Sportsbook
    @State private var isDropdownOpen = false
    
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Sportsbook")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(.secondary)
                
                Spacer()
            }
            .padding(.horizontal)
            .padding(.top, 12)
            
            Button(action: {
                withAnimation(.easeInOut(duration: 0.2)) {
                    isDropdownOpen.toggle()
                }
            }) {
                HStack {
                    // Selected sportsbook display
                    HStack(spacing: 8) {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(SportsbookHelper.color(for: selectedSportsbook))
                            .frame(width: 30, height: 20)
                            .overlay(
                                Text(SportsbookHelper.initials(for: selectedSportsbook))
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(.white)
                            )
                        
                        Text(selectedSportsbook.displayName)
                            .font(.system(size: 14, weight: .medium))
                    }
                    .padding(.vertical, 8)
                    .padding(.horizontal, 12)
                    
                    Spacer()
                    
                    // Dropdown chevron indicator
                    Image(systemName: isDropdownOpen ? "chevron.up" : "chevron.down")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.trailing, 12)
                }
                .background(Color(.systemGray6))
                .cornerRadius(8)
                .padding(.horizontal)
                .padding(.bottom, isDropdownOpen ? 8 : 12)
            }
            
            // Dropdown content
            if isDropdownOpen && availableSportsbooks.count > 1 {
                VStack(spacing: 0) {
                    ForEach(availableSportsbooks.filter { $0 != selectedSportsbook }, id: \.self) { sportsbook in
                        Button(action: {
                            selectedSportsbook = sportsbook
                            withAnimation {
                                isDropdownOpen = false
                            }
                        }) {
                            HStack(spacing: 8) {
                                RoundedRectangle(cornerRadius: 4)
                                    .fill(SportsbookHelper.color(for: sportsbook))
                                    .frame(width: 30, height: 20)
                                    .overlay(
                                        Text(SportsbookHelper.initials(for: sportsbook))
                                            .font(.system(size: 10, weight: .bold))
                                            .foregroundColor(.white)
                                    )
                                
                                Text(sportsbook.displayName)
                                    .font(.system(size: 14, weight: .medium))
                                    .foregroundColor(.primary)
                                
                                Spacer()
                            }
                            .padding(.vertical, 10)
                            .padding(.horizontal, 12)
                            .background(Color(.systemGray6).opacity(0.5))
                            .contentShape(Rectangle())
                        }
                    }
                }
                .padding(.horizontal)
                .padding(.bottom, 12)
                .background(Color(.systemBackground))
                .cornerRadius(8)
                .shadow(color: Color.black.opacity(0.1), radius: 4, x: 0, y: 2)
                .padding(.horizontal)
                .transition(.opacity)
                .zIndex(1) // Ensure dropdown appears on top
            }
        }
        .background(Color(.systemBackground))
        .overlay(
            Rectangle()
                .fill(Color(.systemGray4))
                .frame(height: 1),
            alignment: .bottom
        )
        .onAppear {
            // Default to DraftKings if available, otherwise first available
            if !availableSportsbooks.contains(selectedSportsbook) {
                if availableSportsbooks.contains(.draftkings) {
                    selectedSportsbook = .draftkings
                } else {
                    selectedSportsbook = availableSportsbooks.first ?? .draftkings
                }
            }
        }
    }
}

// MARK: - Sportsbook Helper
struct SportsbookHelper {
    static func color(for sportsbook: Sportsbook) -> Color {
        switch sportsbook {
        case .draftkings:
            return Color(red: 0.0, green: 0.31, blue: 0.15)  // Dark green
        case .fanduel:
            return Color(red: 0.0, green: 0.36, blue: 0.82)  // Blue
        case .betmgm:
            return Color(red: 0.83, green: 0.69, blue: 0.22) // Gold
        case .caesars:
            return Color(red: 0.8, green: 0.0, blue: 0.13)   // Red
        case .pointsbet:
            return Color(red: 0.0, green: 0.2, blue: 0.4)    // Navy blue
        case .barstool:
            return Color(red: 0.95, green: 0.4, blue: 0.76)  // Pink
        // New sportsbook colors
        case .betonlineag:
            return Color(red: 0.0, green: 0.4, blue: 0.6)    // Teal blue
        case .betrivers:
            return Color(red: 0.9, green: 0.35, blue: 0.0)   // Orange
        case .bovada:
            return Color(red: 0.7, green: 0.0, blue: 0.0)    // Dark red
        case .lowvig:
            return Color(red: 0.2, green: 0.6, blue: 0.3)    // Green
        }
    }
    
    static func initials(for sportsbook: Sportsbook) -> String {
        switch sportsbook {
        case .draftkings: return "DK"
        case .fanduel: return "FD"
        case .betmgm: return "MGM"
        case .caesars: return "CZR"
        case .pointsbet: return "PB"
        case .barstool: return "BS"
        // New sportsbook initials
        case .betonlineag: return "BOL"
        case .betrivers: return "BR"
        case .bovada: return "BV"
        case .lowvig: return "LV"
        }
    }
}
