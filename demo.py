#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрационный скрипт для PDF Generator
Показывает основные возможности программы
"""

from pdf_generator import PDFGenerator
from pathlib import Path
import pandas as pd

def demo():
    """Демонстрация основных возможностей PDF Generator"""
    print("🚀 ДЕМОНСТРАЦИЯ PDF GENERATOR")
    print("=" * 50)
    
    generator = PDFGenerator()
    
    # 1. Показываем доступные файлы
    print("\n📁 АНАЛИЗ ДОСТУПНЫХ ФАЙЛОВ:")
    print("-" * 30)
    
    data_files = generator.get_data_files()
    template_files = generator.get_template_files()
    
    print(f"📊 Файлов данных: {len(data_files)}")
    for file in data_files:
        print(f"   • {file.name}")
    
    print(f"\n🎨 HTML шаблонов: {len(template_files)}")
    for file in template_files:
        print(f"   • {file.name}")
    
    if not data_files or not template_files:
        print("\n❌ Не найдены файлы данных или шаблоны!")
        return
    
    # 2. Демонстрируем чтение данных
    print(f"\n📖 ДЕМОНСТРАЦИЯ ЧТЕНИЯ ДАННЫХ:")
    print("-" * 35)
    
    # Читаем CSV
    csv_file = next((f for f in data_files if f.suffix.lower() == '.csv'), None)
    if csv_file:
        print(f"📄 Читаем CSV: {csv_file.name}")
        csv_data = generator.read_csv_file(csv_file)
        if not csv_data.empty:
            print(f"   ✓ Прочитано {len(csv_data)} строк")
            print(f"   ✓ Колонки: {', '.join(csv_data.columns)}")
            
            # Показываем доступные счета
            csv_invoices = generator.get_available_invoices(csv_data)
            print(f"   ✓ Доступные счета: {', '.join(csv_invoices[:3])}{'...' if len(csv_invoices) > 3 else ''}")
    
    # Читаем JSON
    json_file = next((f for f in data_files if f.suffix.lower() == '.json'), None)
    if json_file:
        print(f"\n📄 Читаем JSON: {json_file.name}")
        json_data = generator.read_json_file(json_file)
        if json_data:
            print(f"   ✓ Прочитано {len(json_data)} записей")
            print(f"   ✓ Ключи первой записи: {', '.join(json_data[0].keys())}")
            
            # Показываем доступные счета
            json_invoices = generator.get_available_invoices(json_data)
            print(f"   ✓ Доступные счета: {', '.join(json_invoices)}")
    
    # 3. Демонстрируем генерацию PDF
    print(f"\n📄 ДЕМОНСТРАЦИЯ ГЕНЕРАЦИИ PDF:")
    print("-" * 35)
    
    # Выбираем первый файл и шаблон
    selected_data_file = data_files[0]
    selected_template = template_files[0]
    
    print(f"📊 Используем данные: {selected_data_file.name}")
    print(f"🎨 Используем шаблон: {selected_template.name}")
    
    # Читаем данные
    if selected_data_file.suffix.lower() == '.csv':
        data = generator.read_csv_file(selected_data_file)
    else:
        data = generator.read_json_file(selected_data_file)
    
    if data is None or (isinstance(data, pd.DataFrame) and data.empty) or (isinstance(data, list) and len(data) == 0):
        print("❌ Не удалось прочитать данные!")
        return
    
    # Получаем первый счет
    invoices = generator.get_available_invoices(data)
    if not invoices:
        print("❌ Не найдены доступные счета!")
        return
    
    selected_invoice = invoices[0]
    print(f"📄 Генерируем PDF для счета: {selected_invoice}")
    
    # Фильтруем данные
    filtered_data = generator.filter_data_by_invoice(data, selected_invoice)
    
    # Рендерим шаблон
    html_content = generator.render_template(selected_template, filtered_data, selected_invoice)
    
    # Генерируем PDF
    output_filename = f"demo_invoice_{selected_invoice}_{selected_template.stem}.pdf"
    output_path = generator.output_dir / output_filename
    
    print(f"\n🎯 Создаем PDF: {output_filename}")
    
    if generator.generate_pdf(html_content, output_path, filtered_data, selected_invoice):
        print(f"✅ PDF успешно создан!")
        print(f"📁 Путь: {output_path.absolute()}")
        
        # Показываем информацию о созданном файле
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"📊 Размер файла: {file_size} байт")
        
        print(f"\n🔍 Открываем PDF...")
        generator.open_pdf(output_path)
        
    else:
        print("❌ Ошибка при создании PDF!")
    
    # 4. Показываем итоговую информацию
    print(f"\n📋 ИТОГОВАЯ ИНФОРМАЦИЯ:")
    print("-" * 25)
    print(f"✅ Программа успешно проанализировала файлы")
    print(f"✅ Создан PDF документ")
    print(f"✅ PDF автоматически открыт в системной программе")
    print(f"\n💡 Для интерактивного использования запустите:")
    print(f"   python pdf_generator.py")

if __name__ == "__main__":
    demo()
