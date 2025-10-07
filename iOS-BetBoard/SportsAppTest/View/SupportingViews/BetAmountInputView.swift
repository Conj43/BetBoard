//
//  BetAmountInputView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/27/25.
//


//
//  BetAmountInputView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/27/25.
//

import SwiftUI

struct BetAmountInputView: View {
    let selection: String
    let odds: Double
    @Binding var betAmount: String
    let onConfirm: (Double) -> Void
    
    @Environment(\.dismiss) var dismiss
    @State private var showingError = false
    @State private var errorMessage = ""
    
    private var amount: Double {
        Double(betAmount) ?? 0.0
    }
    
    private var potentialWin: Double {
        guard amount > 0 else { return 0 }
        if odds > 0 {
            return amount * (odds / 100)
        } else {
            return amount * (100 / abs(odds))
        }
    }
    
    private var totalPayout: Double {
        return amount + potentialWin
    }
    
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                // Header
                VStack(spacing: 12) {
                    Text("Track Your Bet")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                    
                    VStack(spacing: 4) {
                        Text(selection)
                            .font(.headline)
                            .fontWeight(.semibold)
                        
                        Text("at \(formatOdds(odds))")
                            .font(.subheadline)
                            .foregroundColor(.blue)
                    }
                }
                .padding(.top)
                
                // Amount Input Section
                VStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Bet Amount")
                            .font(.headline)
                            .fontWeight(.semibold)
                        
                        HStack {
                            Text("$")
                                .font(.title)
                                .foregroundColor(.secondary)
                            
                            TextField("0.00", text: $betAmount)
                                .font(.title)
                                .fontWeight(.medium)
                                .keyboardType(.decimalPad)
                                .textFieldStyle(PlainTextFieldStyle())
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }
                    
                    // Quick Amount Buttons
                    HStack(spacing: 12) {
                        ForEach([25, 50, 100, 250], id: \.self) { quickAmount in
                            Button(action: {
                                betAmount = String(quickAmount)
                            }) {
                                Text("$\(quickAmount)")
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                    .foregroundColor(.blue)
                                    .padding(.horizontal, 16)
                                    .padding(.vertical, 8)
                                    .background(Color.blue.opacity(0.1))
                                    .cornerRadius(20)
                            }
                        }
                    }
                }
                
                // Payout Preview
                if amount > 0 {
                    VStack(spacing: 12) {
                        Divider()
                        
                        VStack(spacing: 8) {
                            HStack {
                                Text("Potential Win:")
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)
                                Spacer()
                                Text("+$\(formatCurrency(potentialWin))")
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                    .foregroundColor(.green)
                            }
                            
                            HStack {
                                Text("Total Payout:")
                                    .font(.headline)
                                    .fontWeight(.semibold)
                                Spacer()
                                Text("$\(formatCurrency(totalPayout))")
                                    .font(.headline)
                                    .fontWeight(.bold)
                                    .foregroundColor(.primary)
                            }
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }
                }
                
                Spacer()
                
                // Action Buttons
                VStack(spacing: 12) {
                    Button(action: confirmBet) {
                        Text("Track Bet")
                            .font(.headline)
                            .fontWeight(.semibold)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(amount > 0 ? Color.blue : Color.gray)
                            .cornerRadius(12)
                    }
                    .disabled(amount <= 0)
                    
                    Button("Cancel") {
                        dismiss()
                    }
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                }
            }
            .padding()
            .navigationBarHidden(true)
            .alert("Invalid Amount", isPresented: $showingError) {
                Button("OK") { }
            } message: {
                Text(errorMessage)
            }
        }
    }
    
    private func confirmBet() {
        guard amount > 0 else {
            errorMessage = "Please enter a valid bet amount greater than $0."
            showingError = true
            return
        }
        
        guard amount <= 10000 else {
            errorMessage = "Bet amount cannot exceed $10,000."
            showingError = true
            return
        }
        
        onConfirm(amount)
        dismiss()
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    private func formatCurrency(_ amount: Double) -> String {
        return String(format: "%.2f", amount)
    }
}

#Preview {
    BetAmountInputView(
        selection: "UNC ML",
        odds: 130,
        betAmount: .constant("325")
    ) { amount in
        print("Confirmed bet for $\(amount)")
    }
}