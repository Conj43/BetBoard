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
            ForEach([BetType.moneyline, BetType.spread, BetType.total], id: \.self) { betType in
                Button(action: {
                    selectedBetType = betType
                }) {
                    VStack(spacing: 6) {
                        Image(systemName: iconForBetType(betType))
                            .font(.title3)
                        
                        Text(betType.displayName)
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
