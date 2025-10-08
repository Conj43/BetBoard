import SwiftUI

struct BetHistoryEmptyStateView: View {
    @State private var showingTrophy = false
    
    var body: some View {
        VStack(spacing: 28) {
            // Trophy cabinet animation
            ZStack {
                // Empty trophy case
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.gray.opacity(0.3), lineWidth: 2)
                    .frame(width: 120, height: 140)
                    .overlay(
                        VStack {
                            Spacer()
                            // Shelves
                            Rectangle()
                                .fill(Color.gray.opacity(0.2))
                                .frame(height: 1)
                            Spacer()
                            Rectangle()
                                .fill(Color.gray.opacity(0.2))
                                .frame(height: 1)
                            Spacer()
                        }
                    )
                
                // Appearing trophy (faded)
                Image(systemName: "trophy.fill")
                    .font(.system(size: 50))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color.yellow.opacity(0.3), Color.orange.opacity(0.3)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .scaleEffect(showingTrophy ? 1.0 : 0.5)
                    .opacity(showingTrophy ? 0.3 : 0)
                    .onAppear {
                        withAnimation(
                            Animation.easeInOut(duration: 1.5)
                                .repeatForever(autoreverses: true)
                        ) {
                            showingTrophy = true
                        }
                    }
            }
            
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
                    
                    Text("Basketball Wisdom")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)
                    
                    Image(systemName: "quote.closing")
                        .font(.caption2)
                }
                .foregroundColor(.secondary)
                
                Text("Every great champion started with their first game. Your betting journey begins with your first tracked bet!")
                    .font(.caption)
                    .italic()
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
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
            
            // Fun fact
            VStack(spacing: 8) {
                HStack(spacing: 6) {
                    Image(systemName: "lightbulb.fill")
                        .font(.caption)
                        .foregroundColor(.yellow)
                    
                    Text("Fun Fact")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)
                }
                
                Text("The NCAA tournament bracket has a 1 in 9.2 quintillion chance of being perfect. Smart tracking improves your odds!")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
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