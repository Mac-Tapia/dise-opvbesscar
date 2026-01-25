#!/bin/bash
# Script para entrenar con CityLearn v2

cd D:\diseñopvbesscar

python -m src.iquitos_citylearn.oe2.train_citylearn_v2 \
    --config D:\diseñopvbesscar\data\oe2\citylearn\training_data\citylearn_config.json \
    --episodes 50 \
    --device cuda \
    --output-dir ./checkpoints/citylearn_v2/

echo "Training completed"
