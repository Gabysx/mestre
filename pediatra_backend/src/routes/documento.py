from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User, Documento
from werkzeug.utils import secure_filename
import os
from datetime import datetime

documento_bp = Blueprint('documento', __name__)

# Configurações de upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

@documento_bp.route('/documentos', methods=['POST'])
@jwt_required()
def upload_documento():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Apenas médica e admin podem fazer upload de documentos
        if user.role not in ['medica', 'admin']:
            return jsonify({'error': 'Sem permissão para fazer upload de documentos'}), 403
        
        # Verificar se o arquivo foi enviado
        if 'arquivo' not in request.files:
            return jsonify({'error': 'Nenhum arquivo foi enviado'}), 400
        
        file = request.files['arquivo']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Validar arquivo
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
        # Verificar tamanho do arquivo
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': 'Arquivo muito grande. Máximo 16MB'}), 400
        
        # Obter dados do formulário
        paciente_id = request.form.get('paciente_id')
        tipo_documento = request.form.get('tipo_documento')
        
        if not paciente_id or not tipo_documento:
            return jsonify({'error': 'paciente_id e tipo_documento são obrigatórios'}), 400
        
        # Verificar se o paciente existe
        paciente = User.query.get(paciente_id)
        if not paciente or paciente.role != 'paciente':
            return jsonify({'error': 'Paciente não encontrado'}), 404
        
        # Criar pasta de upload se não existir
        create_upload_folder()
        
        # Gerar nome seguro para o arquivo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        # Criar subpasta para o paciente
        patient_folder = os.path.join(UPLOAD_FOLDER, f"paciente_{paciente_id}")
        if not os.path.exists(patient_folder):
            os.makedirs(patient_folder)
        
        file_path = os.path.join(patient_folder, filename)
        
        # Salvar arquivo
        file.save(file_path)
        
        # Criar registro no banco de dados
        documento = Documento(
            paciente_id=paciente_id,
            nome_arquivo=file.filename,
            tipo_documento=tipo_documento,
            caminho_arquivo=file_path,
            tamanho_arquivo=file_size,
            uploaded_by=user.id
        )
        
        db.session.add(documento)
        db.session.commit()
        
        return jsonify({
            'message': 'Documento enviado com sucesso',
            'documento': documento.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@documento_bp.route('/documentos', methods=['GET'])
@jwt_required()
def listar_documentos():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        if user.role == 'paciente':
            # Paciente vê apenas seus documentos
            documentos = Documento.query.filter_by(paciente_id=user.id).order_by(Documento.created_at.desc()).all()
        else:
            # Médica e admin veem todos os documentos
            paciente_id = request.args.get('paciente_id', type=int)
            if paciente_id:
                documentos = Documento.query.filter_by(paciente_id=paciente_id).order_by(Documento.created_at.desc()).all()
            else:
                documentos = Documento.query.order_by(Documento.created_at.desc()).all()
        
        return jsonify({
            'documentos': [documento.to_dict() for documento in documentos]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documento_bp.route('/documentos/<int:documento_id>', methods=['GET'])
@jwt_required()
def download_documento(documento_id):
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        documento = Documento.query.get(documento_id)
        if not documento:
            return jsonify({'error': 'Documento não encontrado'}), 404
        
        # Verificar permissões
        if user.role == 'paciente' and documento.paciente_id != user.id:
            return jsonify({'error': 'Sem permissão para acessar este documento'}), 403
        
        # Verificar se o arquivo existe
        if not os.path.exists(documento.caminho_arquivo):
            return jsonify({'error': 'Arquivo não encontrado no servidor'}), 404
        
        return send_file(
            documento.caminho_arquivo,
            as_attachment=True,
            download_name=documento.nome_arquivo
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documento_bp.route('/documentos/<int:documento_id>', methods=['DELETE'])
@jwt_required()
def deletar_documento(documento_id):
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Apenas médica e admin podem deletar documentos
        if user.role not in ['medica', 'admin']:
            return jsonify({'error': 'Sem permissão para deletar documentos'}), 403
        
        documento = Documento.query.get(documento_id)
        if not documento:
            return jsonify({'error': 'Documento não encontrado'}), 404
        
        # Deletar arquivo do sistema de arquivos
        if os.path.exists(documento.caminho_arquivo):
            os.remove(documento.caminho_arquivo)
        
        # Deletar registro do banco de dados
        db.session.delete(documento)
        db.session.commit()
        
        return jsonify({'message': 'Documento deletado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

