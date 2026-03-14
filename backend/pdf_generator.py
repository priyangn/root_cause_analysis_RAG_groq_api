from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
import os

class PDFReportGenerator:
    def __init__(self, analysis_data: dict, output_path: str):
        self.analysis_data = analysis_data
        self.output_path = output_path
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
    def setup_custom_styles(self):
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#3b82f6'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#3b82f6'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14
        ))
    
    def generate_confusion_matrix_chart(self, ml_result: dict) -> str:
        """Generate confusion matrix visualization"""
        try:
            cm_data = ml_result.get('confusion_matrix', {})
            if not cm_data:
                return None
            
            fig, ax = plt.subplots(figsize=(5, 4))
            
            matrix = [
                [cm_data.get('true_negative', 0), cm_data.get('false_positive', 0)],
                [cm_data.get('false_negative', 0), cm_data.get('true_positive', 0)]
            ]
            
            im = ax.imshow(matrix, cmap='Blues')
            
            ax.set_xticks([0, 1])
            ax.set_yticks([0, 1])
            ax.set_xticklabels(['Normal', 'Failure'])
            ax.set_yticklabels(['Normal', 'Failure'])
            
            ax.set_xlabel('Predicted')
            ax.set_ylabel('Actual')
            ax.set_title(f'{ml_result["model_name"]} Confusion Matrix')
            
            # Add text annotations
            for i in range(2):
                for j in range(2):
                    text = ax.text(j, i, matrix[i][j],
                                 ha="center", va="center", color="black", fontsize=14)
            
            plt.colorbar(im, ax=ax)
            plt.tight_layout()
            
            chart_path = f"/tmp/confusion_matrix_{ml_result['model_name'].replace(' ', '_')}.png"
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return chart_path
        except Exception as e:
            print(f"Error generating confusion matrix: {e}")
            return None
    
    def generate_feature_importance_chart(self, ml_result: dict) -> str:
        """Generate feature importance bar chart"""
        try:
            feature_imp = ml_result.get('feature_importance', {})
            if not feature_imp:
                return None
            
            fig, ax = plt.subplots(figsize=(6, 4))
            
            features = list(feature_imp.keys())
            importances = list(feature_imp.values())
            
            ax.barh(features, importances, color='#3b82f6')
            ax.set_xlabel('Importance')
            ax.set_title(f'{ml_result["model_name"]} Feature Importance')
            ax.invert_yaxis()
            
            plt.tight_layout()
            
            chart_path = f"/tmp/feature_importance_{ml_result['model_name'].replace(' ', '_')}.png"
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return chart_path
        except Exception as e:
            print(f"Error generating feature importance chart: {e}")
            return None
    
    def generate(self):
        """Generate the complete PDF report"""
        doc = SimpleDocTemplate(self.output_path, pagesize=letter)
        story = []
        
        # Title Page
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph("CauseSense AI", self.styles['CustomTitle']))
        story.append(Paragraph("Root Cause Analysis Report", self.styles['Heading2']))
        story.append(Spacer(1, 0.5*inch))
        
        # Project info
        project_name = self.analysis_data.get('project_name', 'Untitled Analysis')
        created_at = self.analysis_data.get('created_at', '')
        
        info_data = [
            ['Project:', project_name],
            ['Analysis Date:', datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S') if created_at else 'N/A'],
            ['Status:', self.analysis_data.get('status', 'Unknown')]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(info_table)
        
        story.append(PageBreak())
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles['SectionHeading']))
        
        root_cause = self.analysis_data.get('root_cause', {})
        if root_cause:
            story.append(Paragraph(f"<b>Root Cause:</b> {root_cause.get('root_cause', 'Not determined')}", 
                                 self.styles['CustomBody']))
            story.append(Spacer(1, 0.2*inch))
            
            confidence = root_cause.get('confidence_score', 0) * 100
            story.append(Paragraph(f"<b>Confidence Score:</b> {confidence:.1f}%", 
                                 self.styles['CustomBody']))
            story.append(Spacer(1, 0.3*inch))
            
            # Evidence
            story.append(Paragraph("<b>Evidence:</b>", self.styles['CustomBody']))
            for evidence in root_cause.get('evidence', [])[:5]:
                story.append(Paragraph(f"• {evidence}", self.styles['CustomBody']))
            story.append(Spacer(1, 0.3*inch))
            
            # Preventive Actions
            story.append(Paragraph("<b>Recommended Actions:</b>", self.styles['CustomBody']))
            for action in root_cause.get('preventive_actions', [])[:5]:
                story.append(Paragraph(f"→ {action}", self.styles['CustomBody']))
        
        story.append(PageBreak())
        
        # Anomalies
        anomalies = self.analysis_data.get('anomalies', [])
        if anomalies:
            story.append(Paragraph("Detected Anomalies", self.styles['SectionHeading']))
            story.append(Paragraph(f"Total anomalies detected: {len(anomalies)}", self.styles['CustomBody']))
            story.append(Spacer(1, 0.2*inch))
            
            anomaly_data = [['Parameter', 'Value', 'Threshold', 'Severity', 'Timestamp']]
            for anomaly in anomalies[:10]:
                anomaly_data.append([
                    anomaly.get('parameter', ''),
                    f"{anomaly.get('value', 0):.2f}",
                    f"{anomaly.get('threshold', 0):.2f}",
                    anomaly.get('severity', ''),
                    anomaly.get('timestamp', '')[:20]
                ])
            
            anomaly_table = Table(anomaly_data, colWidths=[1.2*inch, 1*inch, 1*inch, 1*inch, 1.8*inch])
            anomaly_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            story.append(anomaly_table)
            story.append(PageBreak())
        
        # ML Results
        ml_results = self.analysis_data.get('ml_results', [])
        if ml_results:
            story.append(Paragraph("Machine Learning Analysis", self.styles['SectionHeading']))
            
            for ml_result in ml_results:
                story.append(Paragraph(f"<b>{ml_result['model_name']}</b>", self.styles['Heading3']))
                story.append(Paragraph(f"Accuracy: {ml_result['accuracy']*100:.1f}%", self.styles['CustomBody']))
                story.append(Spacer(1, 0.2*inch))
                
                # Confusion Matrix
                cm_chart = self.generate_confusion_matrix_chart(ml_result)
                if cm_chart and os.path.exists(cm_chart):
                    img = Image(cm_chart, width=3.5*inch, height=2.8*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
                
                # Feature Importance
                fi_chart = self.generate_feature_importance_chart(ml_result)
                if fi_chart and os.path.exists(fi_chart):
                    img = Image(fi_chart, width=4*inch, height=2.7*inch)
                    story.append(img)
                
                story.append(Spacer(1, 0.3*inch))
            
            story.append(PageBreak())
        
        # Hypotheses
        hypotheses = self.analysis_data.get('hypotheses', [])
        if hypotheses:
            story.append(Paragraph("Failure Hypotheses", self.styles['SectionHeading']))
            
            for idx, hyp in enumerate(hypotheses[:5], 1):
                story.append(Paragraph(f"<b>Hypothesis {idx}: {hyp.get('title', '')}</b>", 
                                     self.styles['Heading3']))
                story.append(Paragraph(f"Probability: {hyp.get('probability', 0)*100:.1f}%", 
                                     self.styles['CustomBody']))
                story.append(Paragraph(hyp.get('description', ''), self.styles['CustomBody']))
                story.append(Spacer(1, 0.1*inch))
                
                story.append(Paragraph("<b>Evidence:</b>", self.styles['CustomBody']))
                for evidence in hyp.get('evidence', [])[:3]:
                    story.append(Paragraph(f"• {evidence}", self.styles['CustomBody']))
                
                story.append(Spacer(1, 0.3*inch))
        
        # Build PDF
        doc.build(story)
        
        # Clean up temporary chart files
        for ml_result in ml_results:
            model_name = ml_result['model_name'].replace(' ', '_')
            for chart_type in ['confusion_matrix', 'feature_importance']:
                chart_path = f"/tmp/{chart_type}_{model_name}.png"
                if os.path.exists(chart_path):
                    os.remove(chart_path)
        
        return self.output_path
