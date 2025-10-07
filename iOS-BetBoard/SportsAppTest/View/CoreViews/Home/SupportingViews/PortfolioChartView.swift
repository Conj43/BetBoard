//
//  PortfolioChartView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


import SwiftUI
import Charts

struct PortfolioChartView: View {
    let chartData: [ChartDataPoint]
    let totalPnL: Double
    let totalPnLFormatted: String
    let roiFormatted: String
    @Binding var selectedTimeframe: TimeFrame
    let onTimeframeChange: (TimeFrame) -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Portfolio Performance")
                    .font(.headline)
                    .fontWeight(.semibold)
                Spacer()
            }
            
            // Overall P&L Display
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Total P&L")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(totalPnLFormatted)
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(totalPnL >= 0 ? .green : .red)
                }
                
                HStack {
                    Text("ROI")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(roiFormatted)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(totalPnL >= 0 ? .green : .red)
                }
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
            
            // Time Frame Selector
            HStack {
                ForEach(TimeFrame.allCases, id: \.self) { timeframe in
                    Button(action: {
                        selectedTimeframe = timeframe
                        onTimeframeChange(timeframe)
                    }) {
                        Text(timeframe.displayName)
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(selectedTimeframe == timeframe ? .white : .primary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(selectedTimeframe == timeframe ? Color.blue : Color(.systemGray5))
                            .cornerRadius(8)
                    }
                }
            }
            
            // Chart
            Chart(chartData) { dataPoint in
                LineMark(
                    x: .value("Date", dataPoint.date),
                    y: .value("P&L", dataPoint.pnl)
                )
                .foregroundStyle(totalPnL >= 0 ? .green : .red)
                .interpolationMethod(.catmullRom)
            }
            .frame(height: 200)
            .chartXAxis {
                AxisMarks(values: .automatic) { value in
                    AxisGridLine()
                    AxisValueLabel(format: .dateTime.month(.abbreviated).day())
                }
            }
            .chartYAxis {
                AxisMarks { value in
                    AxisGridLine()
                    AxisValueLabel {
                        if let doubleValue = value.as(Double.self) {
                            Text(formatCurrency(doubleValue))
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    private func formatCurrency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencySymbol = "$"
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "$0"
    }
}
