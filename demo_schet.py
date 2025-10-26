#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрационный скрипт для генератора счетов
Показывает основные возможности программы
"""

from schet_generator import SchetGenerator
from pathlib import Path
import pandas as pd

def demo_schet_generator():
    """Демонстрация основных возможностей генератора счетов"""
    print("🚀 ДЕМОНСТРАЦИЯ ГЕНЕРАТОРА СЧЕТОВ")
    print("=" * 50)
    
    generator = SchetGenerator()
    
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
    
    # Читаем CSV с данными счетов
    csv_file = next((f for f in data_files if 'scheta' in f.name.lower()), None)
    if csv_file:
        print(f"📄 Читаем CSV: {csv_file.name}")
        csv_data = generator.read_csv_file(csv_file)
        if not csv_data.empty:
            print(f"   ✓ Прочитано {len(csv_data)} строк")
            print(f"   ✓ Колонки: {', '.join(csv_data.columns)}")
            
            # Показываем доступные счета
            csv_invoices = generator.get_available_invoices(csv_data)
            print(f"   ✓ Доступные счета: {', '.join(csv_invoices[:3])}{'...' if len(csv_invoices) > 3 else ''}")
            
            # Показываем пример данных
            print(f"\n📋 ПРИМЕР ДАННЫХ:")
            print("-" * 20)
            sample_data = csv_data.head(3)
            for _, row in sample_data.iterrows():
                print(f"   • {row['номер_счета']} | {row['клиент']} | {row['товар']} | {row['общая_сумма']} руб.")
    
    # 3. Демонстрируем генерацию PDF
    print(f"\n📄 ДЕМОНСТРАЦИЯ ГЕНЕРАЦИИ PDF:")
    print("-" * 35)
    
    # Выбираем первый файл и шаблон
    selected_data_file = data_files[0]
    selected_template = template_files[0]
    
    print(f"📊 Используем данные: {selected_data_file.name}")
    print(f"🎨 Используем шаблон: {selected_template.name}")
    
    # Читаем данные
    data = generator.read_csv_file(selected_data_file)
    
    if data is None or data.empty:
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
    output_filename = f"demo_schet_{selected_invoice}_{selected_template.stem}.pdf"
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
    
    # 4. Демонстрируем создание нового счета
    print(f"\n🆕 ДЕМОНСТРАЦИЯ СОЗДАНИЯ НОВОГО СЧЕТА:")
    print("-" * 40)
    
    # Создаем тестовые данные для нового счета
    new_items = [
        {
            'товар': 'Принтер HP LaserJet',
            'количество': 1,
            'цена_за_единицу': 25000
        },
        {
            'товар': 'Картридж для принтера',
            'количество': 3,
            'цена_за_единицу': 3000
        }
    ]
    
    customer_name = "ООО 'ТестКлиент'"
    
    print(f"👤 Клиент: {customer_name}")
    print(f"📦 Товары:")
    for item in new_items:
        total = item['количество'] * item['цена_за_единицу']
        print(f"   • {item['товар']} x{item['количество']} = {total:,.2f} руб.")
    
    # Генерируем новый счет
    new_invoice_number = generator.generate_new_invoice(customer_name, new_items)
    
    if new_invoice_number:
        print(f"\n✅ Новый счет создан!")
        print(f"📋 Номер счета: {new_invoice_number}")
    
    # 5. Показываем итоговую информацию
    print(f"\n📋 ИТОГОВАЯ ИНФОРМАЦИЯ:")
    print("-" * 25)
    print(f"✅ Программа успешно проанализировала файлы")
    print(f"✅ Создан PDF документ из существующих данных")
    print(f"✅ Создан новый счет с автоматическим номером")
    print(f"✅ PDF файлы автоматически открыты")
    print(f"\n💡 Для интерактивного использования запустите:")
    print(f"   python schet_generator.py")

def demo_automatic_counter():
    """Демонстрация работы автоматического счетчика"""
    print("\n🔢 ДЕМОНСТРАЦИЯ АВТОМАТИЧЕСКОГО СЧЕТЧИКА:")
    print("-" * 45)
    
    generator = SchetGenerator()
    
    # Показываем несколько номеров счетов
    print("📋 Генерируем несколько номеров счетов:")
    for i in range(3):
        invoice_number = generator.get_next_invoice_number()
        print(f"   {i+1}. {invoice_number}")
    
    print("\n✅ Счетчик работает автоматически!")

if __name__ == "__main__":
    demo_schet_generator()
    demo_automatic_counter()
