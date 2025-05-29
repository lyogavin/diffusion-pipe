#!/bin/bash

# Install script for ffmpeg on macOS
# This script helps install ffmpeg for better video generation compatibility

echo "OpenBor Animation Generator - ffmpeg Installation for macOS"
echo "=========================================================="

# Check if Homebrew is installed
if command -v brew &> /dev/null; then
    echo "✓ Homebrew is installed"
    
    # Check if ffmpeg is already installed
    if command -v ffmpeg &> /dev/null; then
        echo "✓ ffmpeg is already installed"
        ffmpeg -version | head -1
    else
        echo "Installing ffmpeg via Homebrew..."
        brew install ffmpeg
        
        if command -v ffmpeg &> /dev/null; then
            echo "✓ ffmpeg installed successfully!"
            ffmpeg -version | head -1
        else
            echo "✗ ffmpeg installation failed"
            exit 1
        fi
    fi
    
elif command -v port &> /dev/null; then
    echo "✓ MacPorts is installed"
    
    # Check if ffmpeg is already installed
    if command -v ffmpeg &> /dev/null; then
        echo "✓ ffmpeg is already installed"
        ffmpeg -version | head -1
    else
        echo "Installing ffmpeg via MacPorts..."
        sudo port install ffmpeg
        
        if command -v ffmpeg &> /dev/null; then
            echo "✓ ffmpeg installed successfully!"
            ffmpeg -version | head -1
        else
            echo "✗ ffmpeg installation failed"
            exit 1
        fi
    fi
    
else
    echo "Neither Homebrew nor MacPorts found."
    echo ""
    echo "Please install one of the following package managers first:"
    echo ""
    echo "1. Homebrew (recommended):"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo "   Then run: brew install ffmpeg"
    echo ""
    echo "2. MacPorts:"
    echo "   Download from: https://www.macports.org/install.php"
    echo "   Then run: sudo port install ffmpeg"
    echo ""
    echo "3. Download ffmpeg binary directly:"
    echo "   https://ffmpeg.org/download.html#build-mac"
    echo ""
    exit 1
fi

echo ""
echo "ffmpeg is now ready for use with the OpenBor Animation Generator!"
echo "You can now run the animation generator and it will use ffmpeg for better video compatibility." 