//
//  BetTypeFilterView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI

struct BetTypeFilterView: View {
    @Binding var selectedBetType: BetType
    
    var body: some View {
        HStack(spacing: 0) {
            // Define fixed bet types to ensure proper type safety
            let betTypes: [BetType] = [.moneyline, .spread, .total]
            
            ForEach(0..<betTypes.count, id: \.self) { index in
                let betType = betTypes[index]
                Button(action: {
                    selectedBetType = betType
                }) {
                    VStack(spacing: 6) {
                        Image(systemName: iconForBetType(betType))
                            .font(.title3)
                        
                        Text(getBetTypeDisplayName(betType))
                            .font(.subheadline)
                            .fontWeight(.medium)
                    }
                    .foregroundColor(selectedBetType == betType ? .white : .primary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(selectedBetType == betType ? Color.purple : Color(.systemGray6))
                    .animation(.easeInOut(duration: 0.2), value: selectedBetType)
                }
            }
        }
        .cornerRadius(12)
        .padding(.horizontal)
        .padding(.vertical, 8)
    }
    
    // Helper function to get display name for bet types
    private func getBetTypeDisplayName(_ betType: BetType) -> String {
        switch betType {
        case .moneyline:
            return "Moneyline"
        case .spread:
            return "Spread"
        case .total:
            return "Total"
        }
    }
    
    private func iconForBetType(_ betType: BetType) -> String {
        switch betType {
        case .moneyline:
            return "dollarsign.circle"
        case .spread:
            return "chart.line.uptrend.xyaxis"
        case .total:
            return "arrow.up.arrow.down"
        }
    }
}

// Preview provider for SwiftUI canvas
#Preview {
    BetTypeFilterView(selectedBetType: .constant(.moneyline))
}
