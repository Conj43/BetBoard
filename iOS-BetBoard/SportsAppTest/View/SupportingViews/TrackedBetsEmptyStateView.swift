import SwiftUI

struct TrackedBetsEmptyStateView: View {
    @State private var isAnimating = false
    var onBrowseGames: () -> Void
    
    var body: some View {
        VStack(spacing: 28) {
            // Target/goal animation
            ZStack {
                // Outer circles
                ForEach(0..<3) { index in
                    Circle()
                        .stroke(
                            Color.blue.opacity(0.3 - Double(index) * 0.1),
                            lineWidth: 2
                        )
                        .frame(
                            width: 80 + CGFloat(index * 30),
                            height: 80 + CGFloat(index * 30)
                        )
                        .scaleEffect(isAnimating ? 1.2 : 1.0)
                        .opacity(isAnimating ? 0 : 1)
                        .animation(
                            Animation.easeOut(duration: 2.0)
                                .repeatForever(autoreverses: false)
                                .delay(Double(index) * 0.3),
                            value: isAnimating
                        )
                }
                
                // Center target
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [Color.blue, Color.purple],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 80, height: 80)
                    
                    Image(systemName: "target")
                        .font(.system(size: 40))
                        .foregroundColor(.white)
                }
            }
            .frame(height: 180)
            .onAppear {
                isAnimating = true
            }
            
            // Main message
            VStack(spacing: 12) {
                Text("Warm Up Your Portfolio")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.primary)
                
                Text("You haven't tracked any bets yet")
                    .font(.body)
                    .foregroundColor(.secondary)
                
                Text("Find a game and make your first pick!")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            // CTA Button
            Button(action: onBrowseGames) {
                HStack(spacing: 8) {
                    Image(systemName: "magnifyingglass")
                    Text("Browse Games")
                        .fontWeight(.semibold)
                }
                .font(.headline)
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding()
                .background(
                    LinearGradient(
                        colors: [Color.blue, Color.purple],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .cornerRadius(12)
            }
            .padding(.horizontal)
            
            // How it works steps
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Image(systemName: "list.number")
                        .foregroundColor(.blue)
                    
                    Text("How to Get Started")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                
                VStack(spacing: 12) {
                    HowToStep(
                        number: "1",
                        title: "Find a Game",
                        description: "Search for your favorite teams",
                        icon: "magnifyingglass"
                    )
                    
                    HowToStep(
                        number: "2",
                        title: "Pick Your Bet",
                        description: "Choose spread, moneyline, or total",
                        icon: "chart.line.uptrend.xyaxis"
                    )
                    
                    HowToStep(
                        number: "3",
                        title: "Track Performance",
                        description: "Watch your portfolio grow",
                        icon: "chart.bar.fill"
                    )
                }
            }
            .padding()
            .background(Color(.systemBackground))
            .cornerRadius(16)
            .shadow(color: .black.opacity(0.05), radius: 4)
            
            // Motivational stat
            VStack(spacing: 8) {
                HStack(spacing: 6) {
                    Image(systemName: "trophy.fill")
                        .font(.caption)
                        .foregroundColor(.yellow)
                    
                    Text("Did You Know?")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)
                }
                
                Text("Smart bettors track every bet to analyze their performance and improve their strategy")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
        .padding()
    }
}

struct HowToStep: View {
    let number: String
    let title: String
    let description: String
    let icon: String
    
    var body: some View {
        HStack(spacing: 16) {
            // Number badge
            ZStack {
                Circle()
                    .fill(Color.blue.opacity(0.1))
                    .frame(width: 40, height: 40)
                
                Text(number)
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(.blue)
            }
            
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Image(systemName: icon)
                        .font(.caption)
                        .foregroundColor(.blue)
                    
                    Text(title)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.primary)
                }
                
                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
        }
    }
}

#Preview {
    TrackedBetsEmptyStateView {
        print("Browse games tapped")
    }
}