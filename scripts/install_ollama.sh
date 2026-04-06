#!/bin/bash
# =============================================
# Instalador de Ollama + Gemma 4 para Manjaro
# =============================================

set -e

MODEL_PRIMARY="tinyllama"
MODEL_FALLBACK="qwen2:0.5b"

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

# 3. Agregar al PATH
echo ""
echo "📝 Configurando PATH..."
echo 'export PATH="$PATH:/usr/local/bin"' >> ~/.bashrc
export PATH="$PATH:/usr/local/bin"

# 4. Descargar modelos
echo ""
echo "📥 Descargando modelos..."
echo "   Primary: $MODEL_PRIMARY (~400MB - CPU friendly)"
echo "   Fallback: $MODEL_FALLBACK (~400MB)"

# Descargar primary
if ollama pull "$MODEL_PRIMARY" 2>/dev/null; then
    echo "   ✅ $MODEL_PRIMARY descargado"
else
    echo "   ⚠️ $MODEL_PRIMARY falló, descargando fallback..."
    ollama pull "$MODEL_FALLBACK"
    MODEL_PRIMARY="$MODEL_FALLBACK"
fi

# Descargar gemma4:e2b para GPU (opcional)
echo ""
echo "📥 (Opcional) Descargando gemma4:e2b para GPU..."
echo "   Si tienes GPU, ejecuta: ollama pull gemma4:e2b"

# 5. Verificar instalación
echo ""
echo "✅ Modelos instalados:"
ollama list

echo ""
echo "============================================"
echo "🎉 Instalación completada!"
echo "============================================"
echo ""
echo "Para usar Gemma 4:"
echo "  ollama run $MODEL_PRIMARY"
echo ""
echo "Para usar como API:"
echo "  ollama serve"
echo "  # API: http://localhost:11434"
echo ""