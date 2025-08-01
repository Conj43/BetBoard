//
//  FirebaseTestView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


//
//  FirebaseTestView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI
import FirebaseFirestore

struct FirebaseTestView: View {
    @State private var connectionStatus = "Testing..."
    @State private var collections: [String] = []
    @State private var documentCounts: [String: Int] = [:]
    
    var body: some View {
        NavigationView {
            List {
                Section("Connection Status") {
                    Text(connectionStatus)
                        .foregroundColor(connectionStatus.contains("✅") ? .green : .orange)
                }
                
                Section("Collections Found") {
                    if collections.isEmpty {
                        Text("No collections found")
                            .foregroundColor(.secondary)
                    } else {
                        ForEach(collections, id: \.self) { collection in
                            HStack {
                                Text(collection)
                                Spacer()
                                Text("\(documentCounts[collection] ?? 0) docs")
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                }
                
                Section("Actions") {
                    Button("Test Firebase Connection") {
                        testFirebaseConnection()
                    }
                    
                    Button("Check Collections") {
                        checkCollections()
                    }
                }
            }
            .navigationTitle("Firebase Test")
            .onAppear {
                testFirebaseConnection()
                checkCollections()
            }
        }
    }
    
    private func testFirebaseConnection() {
        connectionStatus = "Testing connection..."
        
        Task {
            do {
                let db = Firestore.firestore()
                
                // Try to read from a simple collection
                let snapshot = try await db.collection("teams").limit(to: 1).getDocuments()
                
                await MainActor.run {
                    if snapshot.documents.isEmpty {
                        connectionStatus = "⚠️ Connected but no teams found"
                    } else {
                        connectionStatus = "✅ Connected successfully"
                    }
                }
            } catch {
                await MainActor.run {
                    connectionStatus = "❌ Connection failed: \(error.localizedDescription)"
                }
            }
        }
    }
    
    private func checkCollections() {
        Task {
            let db = Firestore.firestore()
            let collectionsToCheck = ["teams", "games", "bettingLines", "predictions", "betSlips"]
            var foundCollections: [String] = []
            var counts: [String: Int] = [:]
            
            for collection in collectionsToCheck {
                do {
                    let snapshot = try await db.collection(collection).getDocuments()
                    if !snapshot.documents.isEmpty {
                        foundCollections.append(collection)
                        counts[collection] = snapshot.documents.count
                        print("✅ Collection '\(collection)': \(snapshot.documents.count) documents")
                    } else {
                        print("⚠️ Collection '\(collection)': empty")
                    }
                } catch {
                    print("❌ Error checking collection '\(collection)': \(error)")
                }
            }
            
            await MainActor.run {
                self.collections = foundCollections.sorted()
                self.documentCounts = counts
            }
        }
    }
}

#Preview {
    FirebaseTestView()
}