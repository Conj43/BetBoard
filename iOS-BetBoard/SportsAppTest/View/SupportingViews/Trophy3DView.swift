//
//  Trophy3DView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/8/25.
//

import SwiftUI
import WebKit

struct Trophy3DView: View {
    var body: some View {
        TrophyWebView(htmlString: trophy3DHTML)
            .frame(maxWidth: .infinity)
            .background(Color.clear)
    }
}

struct TrophyWebView: UIViewRepresentable {
    let htmlString: String
    
    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        
        let contentController = WKUserContentController()
        contentController.add(context.coordinator, name: "loadTrophy")
        config.userContentController = contentController
        
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.isScrollEnabled = false
        webView.navigationDelegate = context.coordinator
        
        return webView
    }
    
    func updateUIView(_ webView: WKWebView, context: Context) {
        webView.loadHTMLString(htmlString, baseURL: nil)
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
        var parent: TrophyWebView
        
        init(_ parent: TrophyWebView) {
            self.parent = parent
        }
        
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            if message.name == "loadTrophy" {
                loadTrophyModel(webView: message.webView as? WKWebView)
            }
        }
        
        private func loadTrophyModel(webView: WKWebView?) {
            guard let webView = webView else { return }
            
            if let modelPath = Bundle.main.path(forResource: "trophy", ofType: "glb"),
               let modelData = try? Data(contentsOf: URL(fileURLWithPath: modelPath)) {
                
                let base64String = modelData.base64EncodedString()
                let script = """
                window.postMessage({ trophyData: '\(base64String)' }, '*');
                """
                webView.evaluateJavaScript(script, completionHandler: nil)
            } else {
                print("❌ Could not find trophy.glb in bundle")
                let errorScript = """
                document.getElementById('loading').textContent = 'Trophy not found in bundle';
                """
                webView.evaluateJavaScript(errorScript, completionHandler: nil)
            }
        }
    }
}

private let trophy3DHTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: transparent;
        }
        #canvas-container {
            width: 100vw;
            height: 100vh;
        }
        #loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #888;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div id="loading">Loading trophy...</div>
    <div id="canvas-container"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    <script>
        const container = document.getElementById('canvas-container');
        const loadingDiv = document.getElementById('loading');
        
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.z = 5;
        camera.position.y = 2;
        
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setClearColor(0x000000, 0);
        renderer.setSize(window.innerWidth, window.innerHeight);
        container.appendChild(renderer.domElement);
        
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
        directionalLight.position.set(5, 10, 5);
        scene.add(directionalLight);
        
        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
        directionalLight2.position.set(-5, 5, -5);
        scene.add(directionalLight2);
        
        const pointLight = new THREE.PointLight(0xFFD700, 0.6);
        pointLight.position.set(0, 5, 3);
        scene.add(pointLight);
        
        window.webkit.messageHandlers.loadTrophy.postMessage('request');
        
        window.addEventListener('message', function(event) {
            if (event.data && event.data.trophyData) {
                loadTrophyFromBase64(event.data.trophyData);
            }
        });
        
        function loadTrophyFromBase64(base64Data) {
            const loader = new THREE.GLTFLoader();
            const binaryString = atob(base64Data);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            loader.parse(bytes.buffer, '', function(gltf) {
                const trophy = gltf.scene;
                
                // Change all materials to gold color
                trophy.traverse(function(child) {
                    if (child.isMesh) {
                        child.material = new THREE.MeshPhongMaterial({
                            color: 0xFFD700,        // Gold color
                            shininess: 50,          // Shiny surface
                            flatShading: true       // Voxel/blocky look
                        });
                    }
                });
                
                const box = new THREE.Box3().setFromObject(trophy);
                const center = box.getCenter(new THREE.Vector3());
                trophy.position.sub(center);
                
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 5 / maxDim;
                trophy.scale.setScalar(scale);
                
                scene.add(trophy);
                window.trophyObject = trophy;
                loadingDiv.style.display = 'none';
            }, function(error) {
                console.error('Error parsing model:', error);
                loadingDiv.textContent = 'Error loading trophy';
            });
        }
        
        function animate() {
            requestAnimationFrame(animate);
            if (window.trophyObject) {
                window.trophyObject.rotation.y += 0.01;
            }
            renderer.render(scene, camera);
        }
        animate();
        
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
    </script>
</body>
</html>
"""

#Preview {
    ZStack {
        Color(.systemGroupedBackground)
            .ignoresSafeArea()
        
        Trophy3DView()
            .frame(height: 300)
    }
}
