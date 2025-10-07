//
//  QuickActionsView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


import SwiftUI

struct QuickActionsView: View {
    var body: some View {
        NavigationLink(destination: BetHistoryView()) {
            HStack {
                Image(systemName: "clock.fill")
                Text("View Bet History")
            }
            .font(.headline)
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.blue)
            .cornerRadius(12)
        }
    }
}
