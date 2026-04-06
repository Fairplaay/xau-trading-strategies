#!/bin/bash
# =============================================
# Instalador de Ollama + Gemma 4 para Manjaro
# =============================================

set -e

echo "============================================"
echo "🚀 Instalando Ollama + Gemma 4 E2B"
echo "============================================"

# 1. Instalar dependencias
echo ""
echo "📦 Instalando dependencias..."
sudo pacman -Syu --noconfirm
sudo pacman -S --noconfirm curl wget

# 2. Instalar Ollama
echo ""
echo "🔧 Instalando Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# 3. Agregar al PATH (si no se agregó automáticamente)
echo ""
echo "📝 Configurando PATH..."
echo 'export PATH="$PATH:/usr/local/bin"' >> ~/.bashrc
export PATH="$PATH:/usr/local/bin"

# 4. Descargar Gemma 4 E2B
echo ""
echo "📥 Descargando Gemma 4 E2B (~4GB)..."
echo "   Esto puede tomar varios minutos depending on tu internet..."
ollama pull gemma4:e2b

# 5. Verificar instalación
echo ""
echo "✅ Verificando instalación..."
ollama list

echo ""
echo "============================================"
echo "🎉 Instalación completada!"
echo "============================================"
echo ""
echo "Para usar Gemma 4:"
echo "  ollama run gemma4:e2b"
echo ""
echo "Para usar como API (en otro programa):"
echo "  ollama serve"
echo "  # API disponible en http://localhost:11434"
echo ""
echo "Para probar desde Python:"
echo '  import ollama'
echo '  response = ollama.chat(model="gemma4:e2b", messages=[{"role": "user", "content": "Hola"}])'
echo '  print(response["message"]["content"])'
echo ""